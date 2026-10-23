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

# Images shown as columns of the compact grid, in this order. Every other
# image (kernel, secmon, bootloader_ci, ...) is listed in the expanded part only.
GRID_IMAGES = ["firmware", "bootloader", "boardloader", "prodtest"]

# An image delta that differs from the content delta by at least this much
# means an alignment boundary was crossed and is flagged in the report.
BOUNDARY_WARN_BYTES = 4096

COMMENT_MARKER = "<!-- size-comment-Core -->"

SIGNAL_GREW = "\U0001f534"  # red circle
SIGNAL_SHRANK = "\U0001f7e2"  # green circle
SIGNAL_MIXED = "\U0001f7e1"  # yellow circle
SIGNAL_SAME = "⚪"  # white circle
SIGNAL_WARN = "⚠"  # warning sign
NOT_BUILT = "—"  # em dash

# ---------------------------------------------------------------------------
# ELF section headers (ELF32 little endian, which is all the firmware uses)

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
    regions: dict[str, Region]
    warnings: list[str] = field(default_factory=list)

    @property
    def content(self) -> int:
        return self.flash - self.fill

    @property
    def slack(self) -> int:
        # the trailing padding of the last region is the image's own tail padding
        return next(reversed(self.regions.values())).slack if self.regions else 0

    def as_dict(self) -> dict:
        return {
            "flash": self.flash,
            "content": self.content,
            "fill": self.fill,
            "slack": self.slack,
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
    if not inputs:
        regions.setdefault(CODE_REGION, Region()).size += section.size
        regions[CODE_REGION].fill += sum(f.size for f in fills)
        return

    # runs of consecutive inputs belonging to the same region: [(label, start)]
    runs: list[tuple[str, int]] = []
    for item in inputs:
        label = region_of(item.name)
        if not runs or runs[-1][0] != label:
            runs.append((label, item.addr))
    runs[0] = (runs[0][0], section.addr)  # leading padding belongs to the first run

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

    lo = min(s.addr for s in flash_sections)
    hi = max(s.addr + s.size for s in flash_sections)
    ram = sum(s.size for s in elf_sections if s.alloc and not lo <= s.addr < hi)

    warnings: list[str] = []
    regions: dict[str, Region] = {}
    map_path = elf_path.with_suffix(".map")
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
        flash, sum(r.fill for r in regions.values()), ram, regions, warnings
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


def boundary_crossed(old: ImageSize, new: ImageSize) -> bool:
    return (
        abs((new.flash - old.flash) - (new.content - old.content))
        >= BOUNDARY_WARN_BYTES
    )


def changed(old: ImageSize | None, new: ImageSize | None) -> bool:
    if old is None or new is None:
        return old is not new
    return old.content != new.content or old.flash != new.flash or old.ram != new.ram


@dataclass
class Report:
    base: Tree
    new: Tree
    base_label: (
        str | None
    )  # e.g. "main@1a2b3c4"; None when no reference build was found
    base_note: str | None  # e.g. "2 commits behind the base of this PR"
    run_url: str | None

    @property
    def models(self) -> list[str]:
        return sorted({b.model for b in self.new} | {b.model for b in self.base})

    def builds_of(self, model: str) -> list[Build]:
        builds = {b for b in self.new if b.model == model} | {
            b for b in self.base if b.model == model
        }
        return sorted(builds, key=lambda b: (not b.is_release, b))

    def images_of(self, model: str) -> list[str]:
        images = {
            img
            for b in self.builds_of(model)
            for tree in (self.base, self.new)
            for img in tree.get(b, {})
        }
        return [i for i in GRID_IMAGES if i in images] + sorted(
            images - set(GRID_IMAGES)
        )

    def pair(
        self, build: Build, image: str
    ) -> tuple[ImageSize | None, ImageSize | None]:
        return self.base.get(build, {}).get(image), self.new.get(build, {}).get(image)

    def pairs(
        self, model: str, image: str
    ) -> list[tuple[Build, ImageSize | None, ImageSize | None]]:
        found = [(b, *self.pair(b, image)) for b in self.builds_of(model)]
        return [
            (b, old, new) for b, old, new in found if old is not None or new is not None
        ]

    # -- compact grid -------------------------------------------------------

    def cell(self, model: str, image: str) -> str:
        """Signal and content delta of one image across every build of the model."""
        pairs = self.pairs(model, image)
        if not pairs:
            return NOT_BUILT
        if self.base_label is None:
            return fmt(next(n for _b, _o, n in pairs if n is not None).content)
        if all(old is None for _b, old, _n in pairs):
            return "new"
        if all(new is None for _b, _o, new in pairs):
            return "gone"
        complete = [
            (b, old, new)
            for b, old, new in pairs
            if old is not None and new is not None
        ]
        if not complete:
            return "n/a"
        deltas = {b: new.content - old.content for b, old, new in complete}
        sig = signal(deltas.values())
        headline = next((b for b in deltas if b.is_release), next(iter(deltas)))
        text = f"{sig} {fmt_delta(deltas[headline])}"
        if sig == SIGNAL_MIXED:
            text += " mixed"
        if any(boundary_crossed(old, new) for _b, old, new in complete):
            text += f" {SIGNAL_WARN}"
        return text

    def grid(self) -> list[str]:
        lines = [
            "| Model | " + " | ".join(GRID_IMAGES) + " |",
            "| --- |" + " ---: |" * len(GRID_IMAGES),
        ]
        for model in self.models:
            lines.append(
                f"| {model} | "
                + " | ".join(self.cell(model, image) for image in GRID_IMAGES)
                + " |"
            )
        return lines

    def anything_changed(self) -> bool:
        return any(
            changed(old, new)
            for model in self.models
            for image in self.images_of(model)
            for _b, old, new in self.pairs(model, image)
        )

    # -- expanded view ------------------------------------------------------

    def model_summary(self, model: str) -> str:
        """One line naming the images that changed, for the details summary."""
        parts: list[str] = []
        for image in self.images_of(model):
            for build, old, new in self.pairs(model, image):
                if old is None or new is None:
                    parts.append(f"{image} {'new' if old is None else 'gone'}")
                    continue
                delta = new.content - old.content
                if delta or boundary_crossed(old, new):
                    text = f"{image} {fmt_delta(delta)} B"
                    if not build.is_release:
                        text += f" ({build.variant})"
                    if boundary_crossed(old, new):
                        text += (
                            f" {SIGNAL_WARN} image {fmt_delta(new.flash - old.flash)} B"
                        )
                    parts.append(text)
                if build.is_release:
                    break  # the release build speaks for the image unless it is not built there
        return ", ".join(parts) if parts else "no change"

    def details(self, model: str) -> list[str]:
        header = [
            "| Build | Image | Region | Content | Δ content | Image | Δ image | Slack |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
        rows: list[str] = []
        unchanged: list[str] = []
        for build in self.builds_of(model):
            for image in self.images_of(model):
                old, new = self.pair(build, image)
                if new is None and old is None:
                    continue
                if new is None:
                    rows.append(f"| {build.variant} | {image} | gone | | | | | |")
                    continue
                if self.base_label is not None and not changed(old, new):
                    unchanged.append(f"{build.variant} / {image}")
                    continue
                rows += self.image_rows(build, image, old, new)
        if not rows:
            return []  # nothing to expand, the summary line says it all
        lines = header + rows
        if unchanged:
            lines += ["", "Unchanged: " + ", ".join(unchanged)]
        return lines

    def image_rows(
        self, build: Build, image: str, old: ImageSize | None, new: ImageSize
    ) -> list[str]:
        def delta(value: int, before: int | None) -> str:
            return fmt_delta(value - before) if before is not None else "new"

        rows: list[str] = []
        for name, region in new.regions.items():
            before = old.regions.get(name) if old else None
            rows.append(
                f"| {build.variant} | {image} | {name} | {fmt(region.content)} "
                f"| {delta(region.content, before.content if before else None)} | {fmt(region.size)} "
                f"| {delta(region.size, before.size if before else None)} | {fmt(region.slack)} |"
            )
        if len(new.regions) > 1:
            rows.append(
                f"| {build.variant} | {image} | **total** | {fmt(new.content)} "
                f"| {delta(new.content, old.content if old else None)} | {fmt(new.flash)} "
                f"| {delta(new.flash, old.flash if old else None)} | |"
            )
        rows.append(
            f"| {build.variant} | {image} | RAM | {fmt(new.ram)} | {delta(new.ram, old.ram if old else None)} | | | |"
        )
        for warning in new.warnings:
            rows.append(
                f"| {build.variant} | {image} | {SIGNAL_WARN} {warning} | | | | | |"
            )
        return rows

    # -- whole document -----------------------------------------------------

    def markdown(self) -> str:
        out = [COMMENT_MARKER]
        if self.base_label is None:
            title = (
                "**Binary sizes** · no reference build found, sizes of this build only"
            )
        else:
            title = f"**Binary sizes** vs {self.base_label}"
            if self.base_note:
                title += f" ({self.base_note})"
        if self.run_url:
            title += f" · [re-run]({self.run_url})"
        out += [title, ""]

        if self.base_label is not None and not self.anything_changed():
            out.append(f"{SIGNAL_SAME} No binary size changes.")
            return "\n".join(out) + "\n"

        out += self.grid()
        for model in self.models:
            body = self.details(model)
            if not body:
                continue
            summary = (
                self.model_summary(model) if self.base_label is not None else "sizes"
            )
            out += ["", f"<details><summary>{model} — {summary}</summary>", ""]
            out += body
            out += ["", "</details>"]
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
        base, new, args.base_label if base else None, args.base_note, args.run_url
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
