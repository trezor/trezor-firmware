#!/usr/bin/env python3

# script used to generate FontInfo in `rust/src/ui/layout_*/fonts/font_*_*.rs`

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import Path
import click
import json

# pip install freetype-py
import freetype
from mako.template import Template

from foreign_chars import all_languages


def _normalize(s: str) -> str:
    return unicodedata.normalize("NFKC", s)


HERE = Path(__file__).parent
CORE_ROOT = HERE.parent.parent
FONTS_DIR = HERE / "fonts"
RUST_MAKO_TMPL = HERE / "gen_font.mako"
JSON_FONTS_DEST = CORE_ROOT / "translations" / "fonts"
RUST_FONTS_DEST = CORE_ROOT / "embed" / "rust" / "src" / "ui"
LAYOUT_NAME = ""

MIN_GLYPH = ord(" ")
MAX_GLYPH = ord("~")

WRITE_WIDTHS = False

# characters for which bearingX is negative, but we choose to make it zero and modify
# advance instead
MODIFY_BEARING_X = [
    _normalize(c)
    for c in (
        "Ä",
        "À",
        "Â",
        "Ã",
        "Æ",
        "Î",
        "Ï",
        "Ì",
        "î",
        "ï",
        "ì",
        "ÿ",
        "Ý",
        "Ÿ",
        "Á",
        "ý",
        "A",
        "X",
        "Y",
        "j",
        "x",
        "y",
        "}",
        ")",
        ",",
        "/",
        "_",
    )
]

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


def drop_left_columns(buf: list[int], width: int, drop: int) -> list[int]:
    res: list[int] = []
    for i in range(len(buf)):
        if i % width >= drop:
            res.append(buf[i])
    return res


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
        cls, face: freetype.Face, c: str, shaveX: int, inverse_colors: bool = False
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
        width = bitmap.width
        rows = bitmap.rows
        advance = metrics.horiAdvance // 64
        bearingX = metrics.horiBearingX // 64

        remove_left = shaveX
        # discard space on the left side
        if shaveX > 0:
            diff = min(advance, bearingX, shaveX)
            advance -= diff
            bearingX -= diff
            remove_left -= diff
        # the following code is here just for some letters (listed at start)
        # not using negative bearingX makes life so much easier; add it to advance instead
        if bearingX < 0:
            if c in MODIFY_BEARING_X:
                advance += -bearingX
                bearingX = 0
            else:
                raise ValueError(f"Negative bearingX for character '{c}'")
        bearingY = metrics.horiBearingY // 64
        assert advance >= 0 and advance <= 255
        assert bearingX >= 0 and bearingX <= 255
        if bearingY < 0:  # HACK
            print(f"normalizing bearingY {bearingY} for '{c}'")
            bearingY = 0
        assert bearingY >= 0 and bearingY <= 255

        buf = list(bitmap.buffer)
        # discard non-space pixels on the left side
        if remove_left > 0 and width > 0:
            assert bearingX == 0
            buf = drop_left_columns(buf, width, remove_left)
            assert width > remove_left
            width -= remove_left
            assert advance > remove_left
            advance -= remove_left
            print(f'Glyph "{c}": removed {remove_left} pixel columns from the left')

        return Glyph(
            char=c,
            width=width,
            rows=rows,
            advance=advance,
            bearingX=bearingX,
            bearingY=bearingY,
            buf=buf,
            num_grays=bitmap.num_grays,
            inverse_colors=inverse_colors,
        )

    def print_metrics(self) -> None:
        print(
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


class FaceProcessor:
    def __init__(
        self,
        name: str,
        style: str,
        size: int,
        bpp: int = 4,
        shaveX: int = 0,
        ext: str = "ttf",
        gen_normal: bool = True,  # generate font with all the letters
        gen_upper: bool = False,  # generate font with only upper-cased letters
        font_idx: int | None = None,  # idx to UTF-8 foreign chars data
        font_idx_upper: int | None = None,  # idx to UTF-8 upper-cased foreign chars
    ):
        if gen_normal is False and gen_upper is False:
            raise ValueError(
                "At least one must be selected from normal glyphs or only uppercased glyphs."
            )
        print(f"Processing ... {name} {style} {size}")
        self.name = name
        self.style = style
        self.size = size
        self.font_idx = font_idx
        self.font_idx_upper = font_idx_upper
        self.bpp = bpp
        self.shaveX = shaveX
        self.ext = ext
        self.gen_normal = gen_normal
        self.gen_upper = gen_upper

        self.face = freetype.Face(str(FONTS_DIR / f"{name}-{style}.{ext}"))
        self.face.set_pixel_sizes(0, size)  # type: ignore
        self.fontname = f"{name.lower()}_{style.lower()}_{size}"
        self.font_ymin = 0
        self.font_ymax = 0

    @property
    def _name_style_size(self) -> str:
        return f"{self.name}_{self.style}_{self.size}"

    @property
    def _rs_file_name(self) -> Path:
        return (
            RUST_FONTS_DEST
            / f"layout_{LAYOUT_NAME.lower()}"
            / "fonts"
            / f"font_{self.fontname}.rs"
        )

    def _foreign_json_name(self, upper_cased: bool, lang: str) -> str:
        return f"font_{self.fontname}{'_upper' if upper_cased else ''}_{lang}.json"

    def write_files(self) -> None:
        # JSON files:
        if self.gen_normal:
            self.write_foreign_json(upper_cased=False)
        if self.gen_upper:
            self.write_foreign_json(upper_cased=True)
        if WRITE_WIDTHS:
            self.write_char_widths_files()
        self.write_rust_file()

    def write_foreign_json(self, upper_cased=False) -> None:
        for lang, language_chars in all_languages.items():
            fontdata = {}
            for item in language_chars:
                c = _normalize(item)
                map_from = c
                if c.islower() and upper_cased and c != "ß":
                    # FIXME not sure how to properly handle the german "ß"
                    c = c.upper()
                assert len(c) == 1
                assert len(map_from) == 1
                self._load_char(c)
                glyph = Glyph.from_face(self.face, c, self.shaveX)
                glyph.print_metrics()
                fontdata[map_from] = glyph.to_bytes(self.bpp).hex()
            file_name = self._foreign_json_name(upper_cased, lang)
            file = JSON_FONTS_DEST / file_name
            json_content = json.dumps(fontdata, indent=2, ensure_ascii=False)
            file.write_text(json_content + "\n")

    def write_char_widths_files(self) -> None:
        chars: set[str] = set()
        widths: dict[str, int] = {}

        # "normal" ASCII characters
        for i in range(MIN_GLYPH, MAX_GLYPH + 1):
            c = chr(i)
            if c.islower() and not self.gen_normal:
                c = c.upper()
            chars.add(c)
        # foreign language data
        for _lang, lang_chars in all_languages.items():
            for c in lang_chars:
                chars.add(c)

        for c in sorted(chars):
            self._load_char(c)
            glyph = Glyph.from_face(self.face, c, self.shaveX)
            widths[c] = glyph.advance

        filename = f"font_widths_{self.fontname}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json_content = json.dumps(widths, indent=2, ensure_ascii=False)
            f.write(json_content + "\n")

    def _load_char(self, c: str) -> None:
        self.face.load_char(c, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL)  # type: ignore

    # --------------------------------------------------------------------
    # Rust code generation
    # --------------------------------------------------------------------
    def write_rust_file(self) -> None:
        """
        Write a Rust source file using a Mako template.
        """
        # Build a dict with all data needed by the template.
        # 1) Gather ASCII glyph definitions.
        glyphs = []
        for i in range(MIN_GLYPH, MAX_GLYPH + 1):
            c = chr(i)
            if c.islower() and not self.gen_normal:
                continue
            self._load_char(c)
            glyph = Glyph.from_face(self.face, c, self.shaveX)
            arr_bytes = glyph.to_bytes(self.bpp)
            glyphs.append(
                {
                    "ascii": i,
                    "char": glyph.char,
                    "var_name": f"Font_{self._name_style_size}_glyph_{i}",
                    "arr_len": len(arr_bytes),
                    "arr_content": ", ".join(str(n) for n in arr_bytes),
                }
            )

        # 2) Nonprintable glyph.
        self._load_char("?")
        glyph_np = Glyph.from_face(self.face, "?", self.shaveX, inverse_colors=True)
        arr_bytes_np = glyph_np.to_bytes(self.bpp)
        nonprintable = {
            "var_name": f"Font_{self._name_style_size}_glyph_nonprintable",
            "arr_len": len(arr_bytes_np),
            "arr_content": ", ".join(str(n) for n in arr_bytes_np),
        }

        # 3) Build arrays of glyph references.
        glyph_array = []
        glyph_array_upper = []
        if self.gen_normal:
            glyph_array = [
                f"&Font_{self._name_style_size}_glyph_{i}"
                for i in range(MIN_GLYPH, MAX_GLYPH + 1)
            ]
        if self.gen_upper:
            for i in range(MIN_GLYPH, MAX_GLYPH + 1):
                if chr(i).islower():
                    c_to = chr(i).upper()
                    i_mapped = ord(c_to)
                    glyph_array_upper.append(
                        f"&Font_{self._name_style_size}_glyph_{i_mapped}, // {chr(i)} -> {c_to}"
                    )
                else:
                    glyph_array_upper.append(f"&Font_{self._name_style_size}_glyph_{i}")

        # 4) Recompute font_ymin and font_ymax.
        self.font_ymin = 0
        self.font_ymax = 0
        for i in range(MIN_GLYPH, MAX_GLYPH + 1):
            c = chr(i)
            if c.islower() and not self.gen_normal:
                continue
            self._load_char(c)
            glyph = Glyph.from_face(self.face, c, self.shaveX)
            yMin = glyph.bearingY - glyph.rows
            yMax = yMin + glyph.rows
            self.font_ymin = min(self.font_ymin, yMin)
            self.font_ymax = max(self.font_ymax, yMax)

        # 5) Build FontInfo definitions.
        font_info = None
        font_info_upper = None
        if self.gen_normal:
            if self.font_idx is None:
                raise ValueError(
                    f"font_idx must be set when generating FontInfo for {self._name_style_size}"
                )
            font_info = {
                "variant": "normal",
                "translation_blob_idx": self.font_idx,
                "height": self.size,
                "max_height": self.font_ymax - self.font_ymin,
                "baseline": -self.font_ymin,
                "glyph_array": f"Font_{self._name_style_size}",
                "nonprintable": f"Font_{self._name_style_size}_glyph_nonprintable",
            }
        if self.gen_upper:
            if self.font_idx_upper is None:
                raise ValueError(
                    f"font_idx_upper must be set when generating `only_upper` FontInfo for {self._name_style_size}"
                )
            font_info_upper = {
                "variant": "upper",
                "translation_blob_idx": self.font_idx_upper,
                "height": self.size,
                "max_height": self.font_ymax - self.font_ymin,
                "baseline": -self.font_ymin,
                "glyph_array": f"Font_{self._name_style_size}_upper",
                "nonprintable": f"Font_{self._name_style_size}_glyph_nonprintable",
            }

        data = {
            "bpp": self.bpp,
            "name": self._name_style_size,
            "glyphs": glyphs,
            "nonprintable": nonprintable,
            "glyph_array": glyph_array,
            "glyph_array_upper": glyph_array_upper,
            "gen_normal": self.gen_normal,
            "gen_upper": self.gen_upper,
            "font_info": font_info,
            "font_info_upper": font_info_upper,
        }

        # Load the Mako template from the same directory.
        with open(RUST_MAKO_TMPL, "r") as f:
            template_content = f.read()
        template = Template(template_content)
        rendered = template.render(**data)

        # Write the rendered template into the Rust file.
        with open(self._rs_file_name, "wt") as f:
            f.write(rendered)


def gen_layout_bolt():
    global LAYOUT_NAME
    LAYOUT_NAME = "Bolt"
    FaceProcessor("TTHoves", "Regular", 21, ext="otf", font_idx=1).write_files()
    FaceProcessor("TTHoves", "DemiBold", 21, ext="otf", font_idx=5).write_files()
    FaceProcessor(
        "TTHoves",
        "Bold",
        17,
        ext="otf",
        gen_normal=False,
        gen_upper=True,
        font_idx_upper=7,
    ).write_files()
    FaceProcessor("RobotoMono", "Medium", 20, font_idx=3).write_files()


def gen_layout_caesar():
    global LAYOUT_NAME
    LAYOUT_NAME = "Caesar"
    FaceProcessor(
        "PixelOperator",
        "Regular",
        8,
        bpp=1,
        shaveX=1,
        gen_normal=True,
        gen_upper=True,
        font_idx=1,
        font_idx_upper=6,
    ).write_files()
    FaceProcessor(
        "PixelOperator",
        "Bold",
        8,
        bpp=1,
        shaveX=1,
        gen_normal=True,
        gen_upper=True,
        font_idx=2,
        font_idx_upper=7,
    ).write_files()
    FaceProcessor(
        "PixelOperatorMono", "Regular", 8, bpp=1, shaveX=1, font_idx=3
    ).write_files()
    FaceProcessor(
        "Unifont", "Regular", 16, bpp=1, shaveX=1, ext="otf", font_idx=4
    ).write_files()
    # NOTE: Unifont Bold does not seem to have czech characters
    FaceProcessor(
        "Unifont", "Bold", 16, bpp=1, shaveX=1, ext="otf", font_idx=5
    ).write_files()


def gen_layout_delizia():
    global LAYOUT_NAME
    LAYOUT_NAME = "Delizia"
    # FIXME: BIG font id not needed
    FaceProcessor("TTSatoshi", "DemiBold", 42, ext="otf", font_idx=1).write_files()
    FaceProcessor("TTSatoshi", "DemiBold", 21, ext="otf", font_idx=1).write_files()
    FaceProcessor("TTSatoshi", "DemiBold", 18, ext="otf", font_idx=8).write_files()
    FaceProcessor("RobotoMono", "Medium", 21, font_idx=3).write_files()
    FaceProcessor(
        "TTHoves",
        "Bold",
        17,
        ext="otf",
        gen_normal=False,
        gen_upper=True,
        font_idx_upper=7,
    ).write_files()


LAYOUTS = {
    "Bolt": gen_layout_bolt,
    "Caesar": gen_layout_caesar,
    "Delizia": gen_layout_delizia,
}


@click.command()
@click.option(
    "--layout",
    "-l",
    help="Generate fonts only for specified layout",
    type=click.Choice(list(LAYOUTS.keys())),
)
@click.option(
    "--write-widths",
    "-w",
    is_flag=True,
    default=False,
    help="Generate character width files",
)
def main(layout: str | None, write_widths: bool):
    """Generate font files for Trezor firmware."""
    global WRITE_WIDTHS
    WRITE_WIDTHS = write_widths

    if layout:
        click.echo(f"Generating fonts for layout: {layout}")
        LAYOUTS[layout]()
    else:
        click.echo("Generating all fonts")
        for layout_name, layout_func in LAYOUTS.items():
            click.echo(f"\nGenerating {layout_name} layout:")
            layout_func()


if __name__ == "__main__":
    main()
