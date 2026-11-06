#!/usr/bin/env python3
# pyright: reportMissingImports=false
# script used to generate FontInfo in `rust/src/ui/layout_*/fonts/font_*_*.rs`
# and foreign glyphs in `translations/fonts/*/font_*.json`, see `gen_font.toml`

from __future__ import annotations

import json
import logging
import unicodedata
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from itertools import groupby
from pathlib import Path

import click
import freetype
import tomllib
from fontTools.ttLib import TTFont
from foreign_chars import all_languages
from mako.template import Template

LOG = logging.getLogger(__name__)


def _normalize(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _extract_gpos_kerning(font_path: str) -> dict[tuple[int, int], int]:
    """Extract kerning data from GPOS table using fontTools.

    Returns a dict mapping (left_codepoint, right_codepoint) -> kerning_value in font units.
    """
    kerning: dict[tuple[int, int], int] = {}
    try:
        tt = TTFont(font_path)
    except Exception as e:
        LOG.warning(f"Failed to open font {font_path}: {e}")
        return kerning

    with tt:
        if "GPOS" not in tt:
            return kerning

        cmap = tt.getBestCmap()
        if cmap is None:
            return kerning

        # Reverse map: glyph name -> list of codepoints
        glyph_to_codepoints: defaultdict[str, list[int]] = defaultdict(list)
        for cp, glyph_name in cmap.items():
            glyph_to_codepoints[glyph_name].append(cp)

        gpos = tt["GPOS"].table
        for lookup in gpos.LookupList.Lookup:
            for subtable in lookup.SubTable:
                if subtable.Format == 1 and hasattr(subtable, "PairSet"):
                    # PairPos Format 1
                    for i, pair_set in enumerate(subtable.PairSet):
                        left_glyph = subtable.Coverage.glyphs[i]
                        left_cps = glyph_to_codepoints[left_glyph]
                        for pvr in pair_set.PairValueRecord:
                            right_glyph = pvr.SecondGlyph
                            right_cps = glyph_to_codepoints[right_glyph]
                            val = 0
                            if pvr.Value1 and hasattr(pvr.Value1, "XAdvance"):
                                val = pvr.Value1.XAdvance
                            if val != 0:
                                for left_cp in left_cps:
                                    for right_cp in right_cps:
                                        kerning[(left_cp, right_cp)] = val
                elif subtable.Format == 2 and hasattr(subtable, "ClassDef1"):
                    # PairPos Format 2
                    class1 = subtable.ClassDef1.classDefs
                    class2 = subtable.ClassDef2.classDefs
                    coverage_glyphs = set(subtable.Coverage.glyphs)
                    for c1_idx, class1_record in enumerate(subtable.Class1Record):
                        for c2_idx, class2_record in enumerate(
                            class1_record.Class2Record
                        ):
                            val = 0
                            if class2_record.Value1 and hasattr(
                                class2_record.Value1, "XAdvance"
                            ):
                                val = class2_record.Value1.XAdvance
                            if val == 0:
                                continue
                            # Find glyphs in class1 with index c1_idx
                            if c1_idx == 0:
                                left_glyphs = [
                                    g for g in coverage_glyphs if class1.get(g, 0) == 0
                                ]
                            else:
                                left_glyphs = [
                                    g
                                    for g, c in class1.items()
                                    if c == c1_idx and g in coverage_glyphs
                                ]
                            # Find glyphs in class2 with index c2_idx
                            if c2_idx == 0:
                                # Class 0 = all glyphs not explicitly assigned
                                right_glyphs = [
                                    g
                                    for g in glyph_to_codepoints
                                    if class2.get(g, 0) == 0
                                ]
                            else:
                                right_glyphs = [
                                    g for g, c in class2.items() if c == c2_idx
                                ]
                            for left_glyph in left_glyphs:
                                for right_glyph in right_glyphs:
                                    for left_cp in glyph_to_codepoints[left_glyph]:
                                        for right_cp in glyph_to_codepoints[
                                            right_glyph
                                        ]:
                                            kerning[(left_cp, right_cp)] = val

    return kerning


def _extract_gsub_substitutions(font_path: str, features: list[str]) -> dict[int, str]:
    """Map codepoints to the glyph names substituted by the given OpenType features.

    Only single substitutions (e.g. `tnum` for tabular figures) are supported.
    """
    if not features:
        return {}
    with TTFont(font_path) as tt:
        gsub = tt["GSUB"].table
        records = [
            r for r in gsub.FeatureList.FeatureRecord if r.FeatureTag in features
        ]
        missing = set(features) - {r.FeatureTag for r in records}
        if missing:
            raise ValueError(f"Features {missing} not found in {font_path}")
        substitutions: dict[str, str] = {}
        for idx in {idx for r in records for idx in r.Feature.LookupListIndex}:
            for subtable in gsub.LookupList.Lookup[idx].SubTable:
                if subtable.LookupType != 1:
                    raise ValueError(
                        f"Unsupported GSUB lookup type {subtable.LookupType}"
                    )
                substitutions.update(subtable.mapping)
        cmap = tt.getBestCmap()
    assert cmap is not None
    return {cp: substitutions[g] for cp, g in cmap.items() if g in substitutions}


HERE = Path(__file__).parent
CORE_ROOT = HERE.parent.parent
FONTS_DIR = HERE / "fonts"
CONFIG_TOML = HERE / "gen_font.toml"
RUST_MAKO_TMPL = HERE / "gen_font.mako"
JSON_FONTS_DEST = CORE_ROOT / "translations" / "fonts"
RUST_FONTS_DEST = CORE_ROOT / "embed" / "rust" / "src" / "ui"

ASCII = "".join(chr(i) for i in range(ord(" "), ord("~") + 1))

WRITE_WIDTHS = False

# freetype-py defines its enums dynamically, invisible to pyright
FT_LOAD_FLAGS = (
    freetype.FT_LOAD_RENDER  # type: ignore ["FT_LOAD_RENDER" is not a known attribute]
    | freetype.FT_LOAD_TARGET_NORMAL  # type: ignore ["FT_LOAD_TARGET_NORMAL" is not a known attribute]
)
FT_KERNING_DEFAULT = freetype.FT_KERNING_DEFAULT  # type: ignore ["FT_KERNING_DEFAULT" is not a known attribute]

# metrics explanation: https://www.freetype.org/freetype2/docs/glyphs/metrics.png


def process_bitmap_buffer(
    buf: list[int], bpp: int, width: int, height: int
) -> list[int]:
    res = buf[:]
    if bpp == 1:
        if len(res) % 8 != 0:
            # add padding if needed
            for _ in range(8 - len(res) % 8):
                res.append(0)
        res = [
            (
                (a & 0x80)
                | ((b & 0x80) >> 1)
                | ((c & 0x80) >> 2)
                | ((d & 0x80) >> 3)
                | ((e & 0x80) >> 4)
                | ((f & 0x80) >> 5)
                | ((g & 0x80) >> 6)
                | ((h & 0x80) >> 7)
            )
            for a, b, c, d, e, f, g, h in [
                res[i : i + 8] for i in range(0, len(res), 8)
            ]
        ]
    elif bpp == 2:
        if len(res) % 4 != 0:
            # add padding if needed
            for _ in range(4 - len(res) % 4):
                res.append(0)
        res = [
            ((a & 0xC0) | ((b & 0xC0) >> 2) | ((c & 0xC0) >> 4) | ((d & 0xC0) >> 6))
            for a, b, c, d in [res[i : i + 4] for i in range(0, len(res), 4)]
        ]
    elif bpp == 4:
        res: list[int] = []
        for y in range(0, height):
            row = buf[y * width : (y + 1) * width]
            for a, b in zip(row[::2], row[1::2]):
                res.append(((b & 0xF0) | (a >> 4)))
            if width & 1 != 0:
                res.append(row[-1] >> 4)
    elif bpp == 8:
        pass
    else:
        raise ValueError
    return res


@dataclass
class FontConfig:
    """One font entry of `gen_font.toml`, see the keys description there."""

    name: str
    style: str
    size: int
    bpp: int = 4
    shave_x: int = 0
    kerning: bool = False
    font_idx: int | None = None
    font_idx_upper: int | None = None
    nums_only: bool = False
    ascii_subset: str | None = None
    features: list[str] = field(default_factory=list)
    max_advance: int | None = None
    min_spacing: int | None = None
    bitmaps: dict[str, list[str]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.font_idx is None and self.font_idx_upper is None:
            raise ValueError(f"{self.id}: font_idx or font_idx_upper must be set")
        if self.nums_only and self.font_idx is None:
            raise ValueError(f"{self.id}: nums_only requires font_idx")

    @property
    def id(self) -> str:
        return f"{self.name}_{self.style}_{self.size}"


@dataclass
class Glyph:
    char: str
    width: int
    rows: int
    advance: int
    bearingX: int
    bearingY: int
    buf: list[int]
    num_grays: int
    inverse_colors: bool = False

    @classmethod
    def from_face(
        cls, face: freetype.Face, c: str, shave_x: int, inverse_colors: bool = False
    ) -> Glyph:
        assert len(c) == 1
        bitmap = face.glyph.bitmap
        metrics = face.glyph.metrics
        assert metrics.width // 64 == bitmap.width
        assert metrics.height // 64 == bitmap.rows
        assert metrics.width % 64 == 0
        assert metrics.height % 64 == 0
        assert metrics.horiAdvance % 64 == 0
        assert metrics.horiBearingX % 64 == 0
        assert metrics.horiBearingY % 64 == 0
        assert bitmap.width == bitmap.pitch
        assert len(bitmap.buffer) == bitmap.pitch * bitmap.rows
        advance = metrics.horiAdvance // 64
        bearingX = metrics.horiBearingX // 64

        # discard space on the left side (never the pixels of the glyph)
        if shave_x > 0:
            diff = min(advance, bearingX, shave_x)
            advance -= diff
            bearingX -= diff
        # not using negative bearingX makes life so much easier; add it to advance instead
        if bearingX < 0:
            advance += -bearingX
            bearingX = 0
        bearingY = metrics.horiBearingY // 64
        assert 0 <= advance <= 255
        assert 0 <= bearingX <= 255
        if bearingY < 0:  # HACK
            LOG.debug(f"Normalizing bearingY {bearingY} for '{c}'")
            bearingY = 0
        assert 0 <= bearingY <= 255

        return Glyph(
            char=c,
            width=bitmap.width,
            rows=bitmap.rows,
            advance=advance,
            bearingX=bearingX,
            bearingY=bearingY,
            buf=list(bitmap.buffer),
            num_grays=bitmap.num_grays,
            inverse_colors=inverse_colors,
        )

    def replace_bitmap(self, rows: list[str]) -> None:
        """Replace the rendered bitmap with a hand-drawn one ('#' = pixel on)."""
        assert rows and all(len(r) == len(rows[0]) for r in rows)
        self.width = len(rows[0])
        self.rows = len(rows)
        self.buf = [0xFF if px == "#" else 0x00 for row in rows for px in row]

    def log_metrics(self) -> None:
        LOG.debug(
            f'Loaded glyph "{self.char}" ... {self.width} x {self.rows} @ {self.num_grays} grays ({len(self.buf)} bytes, metrics: {self.advance}, {self.bearingX}, {self.bearingY})'
        )

    def process_byte(self, b: int) -> int:
        if self.inverse_colors:
            return b ^ 0xFF
        else:
            return b

    def to_bytes(self, bpp: int) -> bytes:
        infos = [
            self.width,
            self.rows,
            self.advance,
            self.bearingX,
            self.bearingY,
        ]
        if self.buf:
            data = [
                self.process_byte(x)
                for x in process_bitmap_buffer(self.buf, bpp, self.width, self.rows)
            ]
            return bytes(infos + data)
        else:
            return bytes(infos)


@dataclass
class Variant:
    """One `FontInfo` in the Rust file, with its own array of glyph references."""

    suffix: str  # of the `FontInfo` and the glyph array names
    description: str
    blob_idx: int
    # ASCII char -> char of the glyph to show, None for the nonprintable glyph
    mapping: Callable[[str], str | None]


class FaceProcessor:
    def __init__(self, layout: str, cfg: FontConfig) -> None:
        LOG.info(f"Processing {cfg.name} {cfg.style} {cfg.size}")
        self.layout = layout
        self.cfg = cfg
        self.fontname = cfg.id.lower()
        self._unsupported: set[str] = set()  # chars missing in the font

        font_paths = list(FONTS_DIR.glob(f"{cfg.name}-{cfg.style}.[ot]tf"))
        if len(font_paths) != 1:
            raise FileNotFoundError(
                f"Expected one font file {cfg.name}-{cfg.style}.{{otf,ttf}} in {FONTS_DIR}"
            )
        self.font_path = str(font_paths[0])
        self.face = freetype.Face(self.font_path)
        self.face.set_pixel_sizes(0, cfg.size)
        self._substitutions = _extract_gsub_substitutions(self.font_path, cfg.features)

        # Extract GPOS kerning data (preferred over legacy kern table).
        # Values are in font units; convert to pixels using ppem/units_per_em.
        units_per_em = self.face.units_per_EM
        self._gpos_kerning: dict[tuple[int, int], int] = {}
        if units_per_em:
            raw_gpos = _extract_gpos_kerning(self.font_path)
            for (lcp, rcp), val in raw_gpos.items():
                px = round(val * cfg.size / units_per_em)
                if px != 0:
                    self._gpos_kerning[(lcp, rcp)] = px
            if self._gpos_kerning:
                LOG.info(f"  Loaded {len(self._gpos_kerning)} GPOS kerning pairs")

    @property
    def _rs_file_name(self) -> Path:
        return (
            RUST_FONTS_DEST
            / f"layout_{self.layout}"
            / "fonts"
            / f"font_{self.fontname}.rs"
        )

    def _foreign_json_name(self, upper_cased: bool, lang: str) -> str:
        return f"font_{self.fontname}{'_upper' if upper_cased else ''}_{lang}.json"

    def write_files(self) -> None:
        # JSON files:
        if self.cfg.font_idx is not None:
            self.write_foreign_json(upper_cased=False)
        if self.cfg.font_idx_upper is not None:
            self.write_foreign_json(upper_cased=True)
        if "º" in self._unsupported:
            self._unsupported.remove("º")
            LOG.warning(f"{self.cfg.id}: 'º' not supported, using fallback glyph 'o'")
        if self._unsupported:
            LOG.warning(
                f"{self.cfg.id}: characters not supported, using unknown glyph: "
                + " ".join(sorted(self._unsupported))
            )
        if WRITE_WIDTHS:
            self.write_char_widths_files()
        self.write_rust_file()

    def write_foreign_json(self, upper_cased: bool = False) -> None:
        for lang, language_chars in all_languages.items():
            fontdata = {"glyphs": {}, "kernings": []}

            for item in language_chars:
                c = _normalize(item)
                map_from = c
                if c.islower() and upper_cased and c != "ß":
                    # FIXME not sure how to properly handle the german "ß"
                    c = c.upper()
                assert len(c) == 1
                assert len(map_from) == 1

                if not self._char_supported(c):
                    self._unsupported.add(c)
                    if c == "º":
                        c = "o"
                glyph = self.glyph(c)
                glyph.log_metrics()
                fontdata["glyphs"][map_from] = glyph.to_bytes(self.cfg.bpp).hex()

            if self.cfg.kerning:
                # Find kernings across all language characters and ASCII
                all_lang_chars = list(language_chars) + list(ASCII)

                for left_char in all_lang_chars:
                    left_c = _normalize(left_char)

                    if not self._char_supported(left_c):
                        continue

                    if left_c.islower() and upper_cased and left_c != "ß":
                        left_c = left_c.upper()
                    if not self._char_supported(left_c):
                        continue

                    for right_char in all_lang_chars:
                        right_c = _normalize(right_char)
                        if right_c.islower() and upper_cased and right_c != "ß":
                            right_c = right_c.upper()
                        if not self._char_supported(right_c):
                            continue

                        # skip if both are ASCII (handled in .rs file)
                        if left_c in ASCII and right_c in ASCII:
                            continue

                        kern_val = self._get_kerning(ord(left_c), ord(right_c))
                        if kern_val != 0:
                            fontdata["kernings"].append(
                                (left_char, right_char, kern_val)
                            )
                            key = f"{left_char}{right_char}"
                            LOG.debug(
                                f"Special {lang} character kerning for '{key}' : {kern_val} pixels"
                            )

            file_name = self._foreign_json_name(upper_cased, lang)
            layout_fonts_dir = JSON_FONTS_DEST / self.layout
            layout_fonts_dir.mkdir(parents=True, exist_ok=True)
            file = layout_fonts_dir / file_name
            json_content = json.dumps(fontdata, indent=2, ensure_ascii=False)
            file.write_text(json_content + "\n")

    def write_char_widths_files(self) -> None:
        chars: set[str] = set()
        widths: dict[str, int] = {}

        # "normal" ASCII characters
        for c in ASCII:
            if c.islower() and self.cfg.font_idx is None:
                c = c.upper()
            chars.add(c)
        # foreign language data
        for _lang, lang_chars in all_languages.items():
            for c in lang_chars:
                chars.add(c)

        for c in sorted(chars):
            widths[c] = self.glyph(c).advance

        filename = f"font_widths_{self.fontname}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json_content = json.dumps(widths, indent=2, ensure_ascii=False)
            f.write(json_content + "\n")

    def _char_supported(self, c: str) -> bool:
        return self.face.get_char_index(ord(c)) != 0

    def glyph(self, c: str, inverse_colors: bool = False) -> Glyph:
        """Render a glyph, adjusted according to the font config."""
        if ord(c) in self._substitutions:
            name = self._substitutions[ord(c)].encode()
            self.face.load_glyph(self.face.get_name_index(name), FT_LOAD_FLAGS)
        else:
            self.face.load_char(c, FT_LOAD_FLAGS)
        glyph = Glyph.from_face(self.face, c, self.cfg.shave_x, inverse_colors)
        if c in self.cfg.bitmaps:
            glyph.replace_bitmap(self.cfg.bitmaps[c])
        if self.cfg.max_advance is not None:
            glyph.advance = min(glyph.advance, self.cfg.max_advance)
        if self.cfg.min_spacing is not None:
            min_advance = glyph.bearingX + glyph.width + self.cfg.min_spacing
            glyph.advance = max(glyph.advance, min_advance)
        return glyph

    def _get_kerning(self, left_cp: int, right_cp: int) -> int:
        """Get kerning value in pixels for a pair of codepoints.

        GPOS data is preferred; falls back to legacy kern table.
        """
        if self._gpos_kerning:
            val = self._gpos_kerning.get((left_cp, right_cp))
            if val is not None:
                return val
            # If GPOS table exists but has no entry for this pair, return 0
            # (don't fall back to kern table which may have stale/different data)
            return 0
        # Fallback: legacy kern table via freetype
        kerning = self.face.get_kerning(left_cp, right_cp, FT_KERNING_DEFAULT)
        return kerning.x // 64

    def _variants(self) -> list[Variant]:
        cfg = self.cfg
        available = cfg.ascii_subset or ASCII

        def show(c: str) -> str | None:
            if c in available:
                return c
            if c.lower() in available:
                return c.lower()
            return None

        def show_num(c: str) -> str | None:
            return show(c) if c.isdigit() or c == " " else None

        variants = []
        if cfg.font_idx is not None:
            variants.append(Variant("", "normal ASCII", cfg.font_idx, show))
        if cfg.font_idx_upper is not None:
            variants.append(
                Variant(
                    "_upper",
                    "forced uppercase",
                    cfg.font_idx_upper,
                    lambda c: show(c.upper()),
                )
            )
        if cfg.nums_only:
            assert cfg.font_idx is not None
            variants.append(
                Variant("_NumsOnly", "numeral-only ASCII", cfg.font_idx, show_num)
            )
        return variants

    # --------------------------------------------------------------------
    # Rust code generation
    # --------------------------------------------------------------------
    def write_rust_file(self) -> None:
        """
        Write a Rust source file using a Mako template.
        """
        # 1) Glyph references of each FontInfo, as (ASCII code or "nonprintable", comment).
        variants = []
        shown: set[str] = set()
        for variant in self._variants():
            refs = []
            for c in ASCII:
                c_to = variant.mapping(c)
                if c_to is None:
                    refs.append(("nonprintable", None))
                else:
                    shown.add(c_to)
                    refs.append((ord(c_to), f"{c} -> {c_to}" if c_to != c else None))
            variants.append({"variant": variant, "refs": refs})

        # 2) Glyphs referenced by any FontInfo.
        glyphs = []
        for c in sorted(shown):
            glyphs.append(
                {
                    "char": c,
                    "data": list(self.glyph(c).to_bytes(self.cfg.bpp)),
                    "comment": "hand-drawn" if c in self.cfg.bitmaps else None,
                }
            )
        nonprintable = list(self.glyph("?", inverse_colors=True).to_bytes(self.cfg.bpp))

        # 3) Vertical metrics from all ASCII glyphs (regardless of `ascii_subset`).
        font_ymin = 0
        font_ymax = 0
        for c in ASCII:
            if c.islower() and self.cfg.font_idx is None:
                continue
            glyph = self.glyph(c)
            font_ymin = min(font_ymin, glyph.bearingY - glyph.rows)
            font_ymax = max(font_ymax, glyph.bearingY)

        # 4) Kerning of ASCII pairs.
        kernings = []
        if self.cfg.kerning:
            for left in ASCII:
                for right in ASCII:
                    kern_val = self._get_kerning(ord(left), ord(right))
                    if kern_val != 0:
                        kernings.append((ord(left), ord(right), kern_val))
                        LOG.debug(
                            f"left glyph: {left} right glyph:{right} kerning {kern_val}"
                        )
            LOG.info(f"  Number of ASCII kernings: {len(kernings)}")

        # Build two-level kerning structure: index (per left char) + flat pairs.
        # Index stores (left_char, count); start offset is derived as sum of preceding counts.
        kern_index: list[tuple[int, int]] = []  # (left_char, count)
        kern_pairs: list[tuple[int, int]] = []
        for left, group in groupby(
            sorted(kernings, key=lambda x: x[0]), key=lambda x: x[0]
        ):
            pairs = list(group)
            assert len(pairs) <= 255, (
                f"Too many right-char partners ({len(pairs)}) for '{chr(left)}' "
                f"in {self.cfg.id} — exceeds u8 count limit"
            )
            kern_index.append((left, len(pairs)))
            for _, right, val in pairs:
                kern_pairs.append((right, val))

        # Groups for template comments: [(left_char, [(right_char, val), ...]), ...]
        kern_groups = []
        offset = 0
        for left, count in kern_index:
            kern_groups.append((left, kern_pairs[offset : offset + count]))
            offset += count

        data = {
            "name": self.cfg.id,
            "bpp": self.cfg.bpp,
            "notes": self.cfg.notes,
            "glyphs": glyphs,
            "nonprintable": nonprintable,
            "variants": variants,
            "gen_kernings": self.cfg.kerning,
            "kern_index": kern_index,
            "kern_pairs": kern_pairs,
            "kern_groups": kern_groups,
            "height": self.cfg.size,
            "max_height": font_ymax - font_ymin,
            "baseline": -font_ymin,
        }

        template = Template(RUST_MAKO_TMPL.read_text())
        self._rs_file_name.write_text(template.render(**data))  # type: ignore [Argument of type "bytes | str" cannot be assigned to parameter "data" of type "str" in function "write_text"]


def load_config() -> dict[str, list[FontConfig]]:
    with open(CONFIG_TOML, "rb") as f:
        config = tomllib.load(f)
    return {
        layout: [FontConfig(**font) for font in fonts]
        for layout, fonts in config.items()
    }


@click.command()
@click.option(
    "--layout",
    "-l",
    help="Generate fonts only for specified layout",
    type=click.Choice(list(load_config().keys()), case_sensitive=False),
)
@click.option(
    "--write-widths",
    "-w",
    is_flag=True,
    default=False,
    help="Generate character width files",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Print progress and details of the generated glyphs",
)
def main(layout: str | None, write_widths: bool, verbose: bool) -> None:
    """Generate font files for Trezor firmware."""
    global WRITE_WIDTHS
    WRITE_WIDTHS = write_widths
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    if verbose:
        LOG.setLevel(logging.DEBUG)

    for layout_name, fonts in load_config().items():
        if layout is not None and layout.lower() != layout_name:
            continue
        LOG.info(f"Generating {layout_name} layout")
        for font in fonts:
            FaceProcessor(layout_name, font).write_files()


if __name__ == "__main__":
    main()
