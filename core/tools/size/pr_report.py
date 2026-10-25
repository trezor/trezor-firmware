#!/usr/bin/env python3
"""
Compare the sizes of the core firmware images between two sets of CI artifacts
and render the result as a pull request comment.

Both inputs are directories holding one subdirectory per `core-firmware-*`
artifact, as `actions/download-artifact` leaves them. Every artifact holds
`latest/<image>.elf` and `latest/<image>.map` for each image the build produced
(firmware, kernel, secmon, bootloader, boardloader, prodtest, ...).

For every image three numbers are measured:

* image size: bytes written to flash, i.e. the sum of the ELF sections the
  build copies into the `.bin` (listed as `elf_sections` in the project's
  `project.toml`),
* content: image size minus the alignment padding, which the linker reports
  as `*fill*` records in the map file,
* slack: trailing padding up to the next alignment boundary.

The content size is what a code change really adds; the image size is what it
costs in flash, which moves in alignment steps. Inside the firmware image the
kernel and the embedded blobs (nRF app, bootloader) are reported as their own
regions, so a kernel change that crosses the coreapp alignment boundary is
visible as such.

Only the standard library is used so that the script runs on a bare CI runner.
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECTS_DIR = HERE.parents[1] / "embed" / "projects"

ARTIFACT_RE = re.compile(
    r"^core-firmware-(?P<model>[A-Z0-9]+)-(?P<coins>universal|btconly)"
    r"-(?P<kind>normal|debuglink|production)(?P<extra>(?:-[a-z0-9]+)*)$"
)

# Input sections placed into an image as opaque, pre-built blobs. Everything
# else is "code" (for the firmware image: the coreapp).
BLOB_REGIONS = {
    ".kernel": "kernel blob",
    ".nrf_app": "nrf blob",
    ".bootloader": "bootloader blob",
}
CODE_REGION = "code"

# Images shown as columns of the grid, in this order. Any other image that
# changed gets a column of its own, after these.
GRID_IMAGES = ["firmware", "bootloader", "boardloader", "prodtest"]

# Images that are part of the firmware image: they are shown as rows of the
# firmware cell, measured from their own ELF, never as columns.
FOLDED_IMAGES = {"kernel", "secmon"}

# Order of the rows in the firmware cell.
ROW_ORDER = ["coreapp", "kernel", "secmon", "nrf blob", "bootloader blob"]

# An image delta that differs from the content delta by at least this much
# means an alignment boundary was crossed and is flagged in the report.
BOUNDARY_WARN_BYTES = 4096

# An image with less free space than this in its flash area is flagged.
LIMIT_WARN_BYTES = 1024

# Images linked against their own flash area, where free space means something.
# The kernel and the secmon are linked against the whole flash and embedded elsewhere.
AREA_IMAGES = {"firmware", "bootloader", "bootloader_ci", "boardloader", "prodtest"}

COMMENT_MARKER = "<!-- size-comment-Core -->"

# A coloured marker for the kind of change and an arrow for its direction;
# a GitHub comment can carry nothing but native emoji and plain characters.
SIGNAL_GREW = "\U0001f534 \u2191"  # red circle, up
SIGNAL_SHRANK = "\U0001f7e2 \u2193"  # green circle, down
SIGNAL_MIXED = "\U0001f7e1 \u2195"  # yellow circle, up-down
SIGNAL_SAME = "\U0001f535 ="  # blue circle, equals
SIGNAL_WARN = "⚠"  # warning sign
NOT_BUILT = "—"  # em dash

# ---------------------------------------------------------------------------
# ELF section headers (ELF32 little endian, which is all the firmware uses)

SHF_WRITE = 0x1
SHF_ALLOC = 0x2


@dataclass
class ElfSection:
    name: str
    flags: int
    addr: int
    size: int

    @property
    def alloc(self) -> bool:
        return bool(self.flags & SHF_ALLOC)

    @property
    def writable(self) -> bool:
        return bool(self.flags & SHF_WRITE)


def read_elf_sections(path: Path) -> list[ElfSection]:
    data = path.read_bytes()
    if data[:4] != b"\x7fELF" or data[4] != 1 or data[5] != 1:
        raise ValueError(f"{path}: not a little-endian ELF32 file")
    (shoff,) = struct.unpack_from("<I", data, 0x20)
    shentsize, shnum, shstrndx = struct.unpack_from("<HHH", data, 0x2E)
    # section header: name, type, flags, addr, offset, size, ...
    headers = [
        struct.unpack_from("<IIIIII", data, shoff + i * shentsize) for i in range(shnum)
    ]
    strtab_off = headers[shstrndx][4]

    def name_at(idx: int) -> str:
        end = data.index(b"\0", strtab_off + idx)
        return data[strtab_off + idx : end].decode()

    return [
        ElfSection(name_at(name), flags, addr, size)
        for name, _type, flags, addr, _off, size in headers
    ]


# ---------------------------------------------------------------------------
# Project configuration: which sections make up the flash image


def _toml_string_list(text: str, key: str) -> list[str] | None:
    """Value of a one-line `key = ["a", "b"]` entry, enough for project.toml."""
    match = re.search(rf"^\s*{re.escape(key)}\s*=\s*\[(?P<items>[^\]]*)\]", text, re.M)
    if match is None:
        return None
    return re.findall(r'"([^"]*)"', match.group("items"))


def flash_sections_of(image: str, projects_dir: Path) -> list[str]:
    """Names of the sections the build copies into `<image>.bin`."""
    config = projects_dir / image / "project.toml"
    if not config.exists():
        raise FileNotFoundError(
            f"no project.toml for image {image!r} in {projects_dir}"
        )
    text = config.read_text()
    sections = _toml_string_list(text, "elf_sections")
    if sections is None:
        raise ValueError(f"{config}: no elf_sections")
    # STM32F4 firmware is split into two flash banks; the second part has its own list
    return sections + (_toml_string_list(text, "split_part2_sections") or [])


# ---------------------------------------------------------------------------
# Linker map: input sections and fill records per output section

_OUT_SECTION_RE = re.compile(
    r"^(?P<name>\.\S+)(?:\s+0x(?P<addr>[0-9a-f]+)\s+0x(?P<size>[0-9a-f]+))?"
)
_IN_SECTION_RE = re.compile(
    r"^ (?P<name>\.\S+)(?:\s+0x(?P<addr>[0-9a-f]+)\s+0x(?P<size>[0-9a-f]+)\s+\S.*)?$"
)
_FILL_RE = re.compile(r"^ \*fill\*\s+0x(?P<addr>[0-9a-f]+)\s+0x(?P<size>[0-9a-f]+)")
_CONTINUATION_RE = re.compile(
    r"^\s+0x(?P<addr>[0-9a-f]+)\s+0x(?P<size>[0-9a-f]+)(?:\s+\S.*)?$"
)


@dataclass
class MapItem:
    kind: str  # "input" or "fill"
    name: str
    addr: int
    size: int


@dataclass
class MapSection:
    name: str
    addr: int
    size: int
    items: list[MapItem] = field(default_factory=list)

    @property
    def end(self) -> int:
        return self.addr + self.size


_MEMORY_RE = re.compile(
    r"^(?P<name>\S+)\s+0x(?P<origin>[0-9a-f]+)\s+0x(?P<length>[0-9a-f]+)\s+(?P<attrs>\S+)"
)


@dataclass(frozen=True)
class MemoryArea:
    origin: int
    end: int
    writable: bool  # RAM, as opposed to flash

    def holds(self, addr: int) -> bool:
        return self.origin <= addr < self.end


def read_map_memory(path: Path) -> list[MemoryArea]:
    """The regions of the map's Memory Configuration, i.e. the linker script's MEMORY."""
    areas: list[MemoryArea] = []
    started = False
    with path.open(errors="replace") as f:
        for line in f:
            if line.startswith("Linker script and memory map"):
                break
            if not started:
                started = line.startswith("Memory Configuration")
                continue
            match = _MEMORY_RE.match(line)
            if match and match.group("name") != "*default*":
                origin = int(match.group("origin"), 16)
                areas.append(
                    MemoryArea(
                        origin,
                        origin + int(match.group("length"), 16),
                        "w" in match.group("attrs"),
                    )
                )
    return areas


def trailing_fill(section: MapSection) -> int:
    """Padding at the very end of an output section."""
    total = 0
    edge = section.end
    for item in reversed(section.items):
        if item.kind != "fill" or item.addr + item.size != edge:
            break
        total += item.size
        edge = item.addr
    return total


def read_map_sections(path: Path) -> list[MapSection]:
    """Output sections of a GNU ld map with their input sections and fills, in order."""
    sections: list[MapSection] = []
    current: MapSection | None = None
    pending_name: str | None = None  # a section name printed on a line of its own
    pending_is_output = False
    started = False

    def add_item(kind: str, name: str, match: re.Match[str]) -> None:
        if current is not None:
            current.items.append(
                MapItem(
                    kind,
                    name,
                    int(match.group("addr"), 16),
                    int(match.group("size"), 16),
                )
            )

    with path.open(errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if not started:
                started = line.startswith("Linker script and memory map")
                continue

            if pending_name is not None:
                name, is_output, pending_name = pending_name, pending_is_output, None
                cont = _CONTINUATION_RE.match(line)
                if cont:
                    if is_output:
                        current = MapSection(
                            name,
                            int(cont.group("addr"), 16),
                            int(cont.group("size"), 16),
                        )
                        sections.append(current)
                    else:
                        add_item("input", name, cont)
                    continue

            fill = _FILL_RE.match(line)
            if fill:
                add_item("fill", "*fill*", fill)
                continue

            inp = _IN_SECTION_RE.match(line)
            if inp:
                if inp.group("size") is None:
                    pending_name, pending_is_output = inp.group("name"), False
                else:
                    add_item("input", inp.group("name"), inp)
                continue

            out = _OUT_SECTION_RE.match(line)
            if out:
                if out.group("size") is None:
                    pending_name, pending_is_output = out.group("name"), True
                else:
                    current = MapSection(
                        out.group("name"),
                        int(out.group("addr"), 16),
                        int(out.group("size"), 16),
                    )
                    sections.append(current)

    return sections


# ---------------------------------------------------------------------------
# Measurement


@dataclass
class Region:
    size: int = 0  # bytes in the image, padding included
    fill: int = 0  # alignment padding inside and after the region
    slack: int = 0  # trailing padding up to the next boundary

    @property
    def content(self) -> int:
        return self.size - self.fill

    def as_dict(self) -> dict[str, int]:
        return {
            "size": self.size,
            "content": self.content,
            "fill": self.fill,
            "slack": self.slack,
        }


@dataclass
class ImageSize:
    flash: int  # bytes written to flash
    fill: int
    ram: int  # statically allocated RAM
    free: int | None  # free bytes in the image's flash area, None when unknown
    regions: dict[str, Region]
    warnings: list[str] = field(default_factory=list)

    @property
    def content(self) -> int:
        return self.flash - self.fill

    @property
    def near_limit(self) -> bool:
        return self.free is not None and self.free < LIMIT_WARN_BYTES

    def as_dict(self) -> dict:
        return {
            "flash": self.flash,
            "content": self.content,
            "fill": self.fill,
            "free": self.free,
            "ram": self.ram,
            "regions": {
                name: region.as_dict() for name, region in self.regions.items()
            },
            "warnings": self.warnings,
        }


def region_of(input_section: str) -> str:
    for prefix, label in BLOB_REGIONS.items():
        if input_section == prefix or input_section.startswith(prefix + "."):
            return label
    return CODE_REGION


def _split_regions(section: MapSection, regions: dict[str, Region]) -> None:
    """Attribute the address range of one output section to regions.

    Sizes come from addresses, not from the input sections' own sizes: the
    linker merges identical strings across input sections, so those overlap.
    """
    inputs = [i for i in section.items if i.kind == "input"]
    fills = [i for i in section.items if i.kind == "fill"]

    # runs of consecutive inputs belonging to the same region: [(label, start)]
    runs: list[tuple[str, int]] = []
    for item in inputs:
        label = region_of(item.name)
        if not runs or runs[-1][0] != label:
            runs.append((label, item.addr))
    if runs:
        runs[0] = (runs[0][0], section.addr)  # leading padding belongs to the first run
    else:
        # a section without input sections, e.g. the one that pads the
        # bootloader up to its maximum size: all of it is code region padding
        runs.append((CODE_REGION, section.addr))

    for index, (label, start) in enumerate(runs):
        end = runs[index + 1][1] if index + 1 < len(runs) else section.end
        region = regions.setdefault(label, Region())
        region.size += end - start
        inside = [f for f in fills if start <= f.addr < end]
        region.fill += sum(f.size for f in inside)
        # trailing fills: the run of fill records that reach up to the end of the range
        edge = end
        for f in reversed(inside):
            if f.addr + f.size != edge:
                break
            region.slack += f.size
            edge = f.addr


def measure_image(elf_path: Path, projects_dir: Path) -> ImageSize:
    image = elf_path.stem
    flash_names = flash_sections_of(image, projects_dir)
    elf_sections = read_elf_sections(elf_path)
    # a linker script may define several output sections of the same name (e.g. `.flash`)
    flash_sections = [s for s in elf_sections if s.name in flash_names and s.size]
    if not flash_sections:
        raise ValueError(f"{elf_path}: none of {flash_names} present")
    flash = sum(s.size for s in flash_sections)

    warnings: list[str] = []
    map_path = elf_path.with_suffix(".map")
    memory = read_map_memory(map_path) if map_path.exists() else []
    flash_areas = [a for a in memory if not a.writable]
    free: int | None = None
    if flash_areas:
        # `.data` is written to flash but lives in RAM; the map's memory areas tell them apart
        in_flash = [
            s for s in flash_sections if any(a.holds(s.addr) for a in flash_areas)
        ]
        ram = sum(
            s.size
            for s in elf_sections
            if s.alloc and not any(a.holds(s.addr) for a in flash_areas)
        )
        used = [a for a in flash_areas if any(a.holds(s.addr) for s in in_flash)]
        free = sum(
            a.end - max(s.addr + s.size for s in in_flash if a.holds(s.addr))
            for a in used
        )
    else:
        in_flash = flash_sections
        lo = min(s.addr for s in in_flash)
        hi = max(s.addr + s.size for s in in_flash)
        ram = sum(s.size for s in elf_sections if s.alloc and not lo <= s.addr < hi)
    if image not in AREA_IMAGES:
        free = None
    last = max(in_flash, key=lambda s: s.addr)

    regions: dict[str, Region] = {}
    if map_path.exists():
        by_name: dict[str, list[MapSection]] = defaultdict(list)
        for section in read_map_sections(map_path):
            if section.size:
                by_name[section.name].append(section)
        for section in sorted(flash_sections, key=lambda s: s.addr):
            candidates = [
                m for m in by_name.get(section.name, []) if m.addr == section.addr
            ]
            if not candidates:
                warnings.append(
                    f"section {section.name} at {section.addr:#x} missing from the map"
                )
                regions.setdefault(CODE_REGION, Region()).size += section.size
                continue
            mapped = candidates[0]
            if section is last and free is not None:
                free += trailing_fill(mapped)  # a bootloader is padded up to its limit
            if mapped.size != section.size:
                warnings.append(
                    f"section {section.name}: map says {mapped.size} B, ELF says {section.size} B"
                )
            _split_regions(mapped, regions)
        accounted = sum(r.size for r in regions.values())
        if accounted != flash:
            warnings.append(f"map accounts for {accounted} of {flash} B")
    else:
        warnings.append("no map file, padding unknown")
        regions[CODE_REGION] = Region(size=flash)

    return ImageSize(
        flash, sum(r.fill for r in regions.values()), ram, free, regions, warnings
    )


@dataclass(frozen=True, order=True)
class Build:
    model: str
    coins: str
    kind: str
    extra: str  # "", "-miniscript", "-n1w1", ...

    @property
    def variant(self) -> str:
        parts = (
            [self.coins]
            + ([self.kind] if self.kind != "normal" else [])
            + [self.extra.lstrip("-")]
        )
        return " ".join(p for p in parts if p)

    @property
    def is_release(self) -> bool:
        return self.coins == "universal" and self.kind == "normal" and not self.extra

    @property
    def sort_key(self) -> tuple[bool, bool, int, str]:
        kinds = ["normal", "debuglink", "production"]
        return (
            not self.is_release,
            self.coins != "universal",
            kinds.index(self.kind),
            self.extra,
        )


def find_builds(root: Path | None) -> Iterator[tuple[Build, Path]]:
    if root is None or not root.is_dir():
        return
    for entry in sorted(root.iterdir()):
        match = ARTIFACT_RE.match(entry.name)
        if match and entry.is_dir():
            yield Build(**match.groupdict()), entry


Tree = dict[Build, dict[str, ImageSize]]


def measure_tree(root: Path | None, projects_dir: Path) -> Tree:
    """Every image of every build under `root`: {build: {image: size}}."""
    result: Tree = {}
    for build, directory in find_builds(root):
        images: dict[str, ImageSize] = {}
        for elf in sorted(directory.glob("**/*.elf")):
            try:
                images[elf.stem] = measure_image(elf, projects_dir)
            except (FileNotFoundError, ValueError) as e:
                print(f"skipping {elf}: {e}", file=sys.stderr)
        result[build] = images
    return result


# ---------------------------------------------------------------------------
# Report


def fmt(n: int) -> str:
    return f"{n:,}".replace(",", " ")  # narrow no-break space as thousands separator


def fmt_delta(n: int) -> str:
    if n == 0:
        return "0"
    return f"{'+' if n > 0 else '-'}{fmt(abs(n))}"


def fmt_signed(n: int) -> str:
    """A delta with its colour: red when it grew, green when it shrank."""
    if n == 0:
        return "0"
    return f"{SIGNAL_GREW if n > 0 else SIGNAL_SHRANK} {fmt_delta(n)}"


def signal(deltas: Iterable[int]) -> str:
    grew = shrank = False
    for d in deltas:
        grew |= d > 0
        shrank |= d < 0
    if grew and shrank:
        return SIGNAL_MIXED
    if grew:
        return SIGNAL_GREW
    if shrank:
        return SIGNAL_SHRANK
    return SIGNAL_SAME


# ---------------------------------------------------------------------------
# What the report shows per build and image


@dataclass
class Row:
    name: str
    content: int
    size: int
    slack: int


@dataclass
class View:
    """One image of one build as the comment presents it."""

    content: int
    flash: int
    ram: int
    free: int | None
    rows: list[Row]  # region rows; empty for an image with a single region
    warnings: list[str]

    @property
    def near_limit(self) -> bool:
        return self.free is not None and self.free < LIMIT_WARN_BYTES


def tail_slack(image: ImageSize) -> int:
    return next(reversed(image.regions.values())).slack if image.regions else 0


def firmware_view(images: dict[str, ImageSize]) -> View:
    """The firmware with the kernel and the secmon as rows of their own.

    The kernel rides inside the kernel blob of the firmware image; the secmon
    is flashed next to the firmware unless the blob is big enough to hold it.
    Measured from their own ELFs their content is exact, while the blob only
    shows padded steps.
    """
    firmware = images["firmware"]
    rows: list[Row] = []
    warnings = list(firmware.warnings)
    flash = firmware.flash
    for name, region in firmware.regions.items():
        if name == "kernel blob" and "kernel" in images:
            kernel, secmon = images["kernel"], images.get("secmon")
            inside = secmon is not None and region.size >= kernel.flash + secmon.flash
            room = (
                region.size - kernel.flash - (secmon.flash if secmon and inside else 0)
            )
            rows.append(Row("kernel", kernel.content, kernel.flash, room))
            warnings += kernel.warnings
            if secmon:
                rows.append(
                    Row("secmon", secmon.content, secmon.flash, tail_slack(secmon))
                )
                warnings += secmon.warnings
                if not inside:
                    flash += (
                        secmon.flash
                    )  # a separate image, counted with the firmware's
            continue
        rows.append(
            Row(
                "coreapp" if name == CODE_REGION else name,
                region.content,
                region.size,
                region.slack,
            )
        )
    rows.sort(
        key=lambda r: ROW_ORDER.index(r.name) if r.name in ROW_ORDER else len(ROW_ORDER)
    )
    return View(
        sum(r.content for r in rows), flash, firmware.ram, firmware.free, rows, warnings
    )


def view_of(images: dict[str, ImageSize], image: str) -> View | None:
    if image not in images:
        return None
    if image == "firmware":
        return firmware_view(images)
    size = images[image]
    rows = (
        [Row(n, r.content, r.size, r.slack) for n, r in size.regions.items()]
        if len(size.regions) > 1
        else []
    )
    return View(size.content, size.flash, size.ram, size.free, rows, size.warnings)


def boundary_crossed(old: View, new: View) -> bool:
    return (
        abs((new.flash - old.flash) - (new.content - old.content))
        >= BOUNDARY_WARN_BYTES
    )


def changed(old: View | None, new: View | None) -> bool:
    if old is None or new is None:
        return old is not new
    return old.content != new.content or old.flash != new.flash or old.ram != new.ram


Pair = tuple[Build, View | None, View | None]


def md_table(columns: list[tuple[str, bool]], rows: list[list[str]]) -> list[str]:
    """A markdown table; (title, right-aligned) per column."""
    lines = [
        "| " + " | ".join(t for t, _r in columns) + " |",
        "|" + "|".join(" ---: " if r else " --- " for _t, r in columns) + "|",
    ]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return lines


# ---------------------------------------------------------------------------
# Report


@dataclass
class Report:
    base: Tree
    new: Tree
    base_label: (
        str | None
    )  # e.g. "main@1a2b3c4"; None when no reference build was found
    base_note: str | None  # e.g. "2 commits behind the base of this PR"
    run_url: str | None
    incomplete: bool = (
        False  # the reference build did not succeed, some of its images may be missing
    )

    @property
    def missing(self) -> str:
        """What a build without a counterpart on the reference side is called."""
        return "no reference" if self.incomplete else "new"

    @property
    def models(self) -> list[str]:
        return sorted({b.model for b in self.new} | {b.model for b in self.base})

    def builds_of(self, model: str) -> list[Build]:
        builds = {b for b in self.new if b.model == model} | {
            b for b in self.base if b.model == model
        }
        return sorted(builds, key=lambda b: b.sort_key)

    def images_of(self, model: str) -> list[str]:
        images = {
            img
            for b in self.builds_of(model)
            for tree in (self.base, self.new)
            for img in tree.get(b, {})
        }
        images -= FOLDED_IMAGES
        return [i for i in GRID_IMAGES if i in images] + sorted(
            images - set(GRID_IMAGES)
        )

    def pairs(self, model: str, image: str) -> list[Pair]:
        found = [
            (
                b,
                view_of(self.base.get(b, {}), image),
                view_of(self.new.get(b, {}), image),
            )
            for b in self.builds_of(model)
        ]
        return [
            (b, old, new) for b, old, new in found if old is not None or new is not None
        ]

    def columns(self) -> list[str]:
        extra = {
            image
            for model in self.models
            for image in self.images_of(model)
            if image not in GRID_IMAGES
            and any(changed(old, new) for _b, old, new in self.pairs(model, image))
        }
        return GRID_IMAGES + sorted(extra)

    def anything_changed(self) -> bool:
        return any(
            changed(old, new)
            for model in self.models
            for image in self.images_of(model)
            for _b, old, new in self.pairs(model, image)
        )

    def delta(self, value: int, before: int | None) -> str:
        if self.base_label is None:
            return ""
        return fmt_signed(value - before) if before is not None else "new"

    # -- the grid -----------------------------------------------------------

    @staticmethod
    def movers(old: View, new: View) -> list[int]:
        """The deltas one build is judged by: every row's content and the whole image.

        The image delta includes padding and alignment, so it is not the sum of
        the rows: a small kernel change that crosses the coreapp boundary moves
        the image by a whole alignment step, and that is the delta to headline.
        """
        before = {r.name: r for r in old.rows}
        rows = [
            r.content - before[r.name].content for r in new.rows if r.name in before
        ]
        return (rows or [new.content - old.content]) + [new.flash - old.flash]

    def summary(self, pairs: list[Pair]) -> str:
        """Signal and the biggest delta across every build and row of one image."""
        near_limit = any(new.near_limit for _b, _o, new in pairs if new)
        warn = f" {SIGNAL_WARN}" if near_limit else ""
        if self.base_label is None:
            release = next(
                (n for b, _o, n in pairs if b.is_release and n),
                next(n for _b, _o, n in pairs if n),
            )
            return fmt(release.content) + warn
        if all(old is None for _b, old, _n in pairs):
            return self.missing + warn
        if all(new is None for _b, _o, new in pairs):
            return "gone"
        added = sum(old is None for _b, old, _n in pairs)
        removed = sum(new is None for _b, _o, new in pairs)
        changes = ""
        if added:
            changes += (
                f" +{added} variant{'s' if added > 1 else ''}"
                if not self.incomplete
                else f" ({added} without reference)"
            )
        if removed:
            changes += f" -{removed} variant{'s' if removed > 1 else ''}"
        deltas = [
            d for _b, old, new in pairs if old and new for d in self.movers(old, new)
        ]
        if not deltas:
            return "n/a" + changes
        sig = signal(deltas)
        headline = (
            max(deltas) if max(deltas) > 0 else min(deltas)
        )  # growth has priority
        text = f"{sig} {fmt_delta(headline)}"
        crossed = any(
            boundary_crossed(old, new) for _b, old, new in pairs if old and new
        )
        # the limit warning is for changes this PR makes, not a permanent badge
        if crossed or (near_limit and sig != SIGNAL_SAME):
            text += f" {SIGNAL_WARN}"
        return text + changes

    def grid(self) -> list[str]:
        columns = self.columns()
        lines = [
            "| Model | " + " | ".join(columns) + " |",
            "| --- |" + " ---: |" * len(columns),
        ]
        for model in self.models:
            cells = [
                self.summary(self.pairs(model, image))
                if self.pairs(model, image)
                else NOT_BUILT
                for image in columns
            ]
            lines.append(f"| {model} | " + " | ".join(cells) + " |")
        return lines

    # -- the details --------------------------------------------------------

    def hover_cell(self, value: int, before: int | None) -> str:
        """The delta, with the absolute size as the tooltip."""
        if self.base_label is None:
            return fmt(value)
        if before is None:
            return fmt(value)  # nothing to compare with: the size itself
        return f'<span title="{fmt(value)} B">{fmt_signed(value - before)}</span>'

    def image_table(self, pairs: list[Pair]) -> list[str]:
        """Deltas of one image, a row per variant.

        Columns are the firmware's regions (the blobs only when one changed),
        the whole image, RAM and free space; the absolute sizes are the
        tooltips of the cells.
        """
        builds = [(b, old, new) for b, old, new in pairs if new is not None]
        several = len(pairs) > 1

        def row_of(view: View | None, name: str) -> Row | None:
            return (
                next((r for r in view.rows if r.name == name), None) if view else None
            )

        names: list[str] = []
        for _b, _o, new in builds:
            names += [r.name for r in new.rows if r.name not in names]
        names.sort(
            key=lambda n: ROW_ORDER.index(n) if n in ROW_ORDER else len(ROW_ORDER)
        )
        wanted = []
        for name in names:
            moved = any(
                (before := row_of(old, name)) is not None
                and (after := row_of(new, name)) is not None
                and before.content
                != after.content  # padding shifts of a blob are not a change
                for _b, old, new in builds
            )
            if (
                name in ("coreapp", "kernel", "secmon")
                or moved
                or self.base_label is None
            ):
                wanted.append(name)

        columns = ([("Variant", False)] if several else []) + [
            (n, True) for n in wanted
        ]
        if not wanted:
            columns.append(
                ("content", True)
            )  # no regions: the content delta needs a column of its own
        columns += [("image", True), ("RAM", True), ("free", True)]
        rows: list[list[str]] = []
        for build, old, new in builds:
            label = build.variant + (f" ({self.missing})" if old is None else "")
            cells = [label] if several else []
            for name in wanted:
                after, before = row_of(new, name), row_of(old, name)
                cells.append(
                    self.hover_cell(after.content, before.content if before else None)
                    if after
                    else NOT_BUILT
                )
            if not wanted:
                cells.append(self.hover_cell(new.content, old.content if old else None))
            cells.append(self.hover_cell(new.flash, old.flash if old else None))
            cells.append(self.hover_cell(new.ram, old.ram if old else None))
            cells.append(
                ""
                if new.free is None
                else (f"{SIGNAL_WARN} " if new.near_limit else "") + fmt(new.free)
            )
            rows.append(cells)
        for build, _old, new in pairs:
            if new is None:
                rows.append(
                    ([build.variant] if several else [])
                    + ["gone"]
                    + [""] * (len(columns) - 2 - (1 if several else 0))
                )
        return md_table(columns, rows)

    def model_block(self, model: str) -> list[str]:
        """A collapsed block with a table for every image of the model that changed.

        The block starts with its `<details>` line and ends with `</details>`,
        no blank lines around, so that consecutive blocks share one HTML block
        and nothing is rendered between the rows.
        """
        parts: list[str] = []
        for image in self.images_of(model):
            pairs = self.pairs(model, image)
            if not pairs or (
                self.base_label is not None
                and not any(changed(old, new) for _b, old, new in pairs)
            ):
                continue
            parts += [f"### {image}", ""]
            if all(new is None for _b, _o, new in pairs):
                parts += ["gone", ""]
                continue
            parts += self.image_table(pairs) + [""]
            warnings = sorted({w for _b, _o, new in pairs if new for w in new.warnings})
            parts += [f"{SIGNAL_WARN} {w}" for w in warnings] + (
                [""] if warnings else []
            )
        if not parts:
            return []
        return [f"<details><summary>{model}</summary>", ""] + parts + ["</details>"]

    # -- whole document -----------------------------------------------------

    def markdown(self) -> str:
        out = [COMMENT_MARKER]
        if self.base_label is None:
            title = "**Binary sizes** \u00b7 no reference build found, sizes of this build only"
        else:
            title = f"**Binary sizes** vs {self.base_label}"
            notes = [
                n
                for n in (
                    self.base_note,
                    "reference build incomplete" if self.incomplete else "",
                )
                if n
            ]
            if notes:
                title += f" ({', '.join(notes)})"
        if self.run_url:
            title += f" \u00b7 [re-run]({self.run_url})"
        out += [title, ""]
        if self.base_label is not None and not self.anything_changed():
            out.append(f"{SIGNAL_SAME.split()[0]} No binary size changes.")
            return "\n".join(out) + "\n"
        out += self.grid() + [""]
        blocks = [line for model in self.models for line in self.model_block(model)]
        if blocks:
            out += ["<details><summary>Details</summary>"] + blocks + ["</details>"]
        return "\n".join(out) + "\n"

    def as_dict(self) -> dict:
        def tree(src: Tree) -> dict:
            return {
                f"{b.model}-{b.coins}-{b.kind}{b.extra}": {
                    img: size.as_dict() for img, size in images.items()
                }
                for b, images in src.items()
            }

        return {
            "base": self.base_label,
            "base_note": self.base_note,
            "sizes": {"base": tree(self.base), "new": tree(self.new)},
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--new",
        type=Path,
        required=True,
        help="downloaded artifacts of the build under review",
    )
    parser.add_argument(
        "--base", type=Path, help="downloaded artifacts of the reference build"
    )
    parser.add_argument(
        "--base-label", help="how to call the reference build, e.g. main@1a2b3c4"
    )
    parser.add_argument(
        "--base-note", help="caveat about the reference, e.g. '2 commits behind base'"
    )
    parser.add_argument(
        "--run-url", help="link to the workflow run, for re-running the comparison"
    )
    parser.add_argument(
        "--reference-incomplete",
        action="store_true",
        help="the reference build did not succeed: builds it lacks are not new",
    )
    parser.add_argument(
        "--projects",
        type=Path,
        default=PROJECTS_DIR,
        help="core/embed/projects directory",
    )
    parser.add_argument(
        "--markdown", type=Path, help="write the markdown report here (default: stdout)"
    )
    parser.add_argument("--json", type=Path, help="write the raw measurements here")
    args = parser.parse_args()

    new = measure_tree(args.new, args.projects)
    if not new:
        print(f"no core-firmware-* artifacts under {args.new}", file=sys.stderr)
        return 1
    base = measure_tree(args.base, args.projects)
    report = Report(
        base,
        new,
        args.base_label if base else None,
        args.base_note,
        args.run_url,
        args.reference_incomplete,
    )

    text = report.markdown()
    if args.markdown:
        args.markdown.write_text(text)
    else:
        sys.stdout.write(text)
    if args.json:
        args.json.write_text(json.dumps(report.as_dict(), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
