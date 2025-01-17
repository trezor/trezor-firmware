#!/usr/bin/env python3

# script used to generate core/embed/gfx/fonts/font_*_*.c

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO
import json
import sys

# pip install freetype-py
import freetype

from foreign_chars import all_languages


def _normalize(s: str) -> str:
    return unicodedata.normalize("NFKC", s)


HERE = Path(__file__).parent
CORE_ROOT = HERE.parent.parent
FONTS_DIR = HERE / "fonts"
OUT_DIR = HERE / ".." / ".." / "embed" / "gfx" / "fonts"
C_FONTS_DEST = CORE_ROOT / "embed" / "gfx" / "fonts"
JSON_FONTS_DEST = CORE_ROOT / "translations" / "fonts"

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

    def get_definition_line(
        self,
        name_style_size: str,
        bpp: int,
        i: int | str,
        static: bool = True,
    ) -> str:
        numbers = ", ".join(str(n) for n in self.to_bytes(bpp))
        comment = f"/* {self.char} */"
        const_name = f"Font_{name_style_size}_glyph_{i}"
        if static:
            modifier = "static const"
        else:
            modifier = "const"
        return f"{comment} {modifier} uint8_t {const_name}[] = {{ {numbers} }};\n"

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
    ):
        if gen_normal is False and gen_upper is False:
            raise ValueError(
                "At least one must be selected from normal glyphs or only uppercased glyphs."
            )
        print(f"Processing ... {name} {style} {size}")
        self.name = name
        self.style = style
        self.size = size
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
    def _c_file_name(self) -> Path:
        return C_FONTS_DEST / f"font_{self.fontname}.c"

    @property
    def _h_file_name(self) -> Path:
        return C_FONTS_DEST / f"font_{self.fontname}.h"

    def write_files(self) -> None:
        self.write_c_files()
        if self.gen_normal:
            self.write_foreign_json(upper_cased=False)
        if self.gen_upper:
            self.write_foreign_json(upper_cased=True)
        if WRITE_WIDTHS:
            self.write_char_widths_files()

    def write_c_files(self) -> None:
        self._write_c_file()
        self._write_h_file()

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
            file = (
                JSON_FONTS_DEST
                / f"font_{self.fontname}{'_upper' if upper_cased else ''}_{lang}.json"
            )
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

    def _write_c_file(self) -> None:
        with open(OUT_DIR / self._c_file_name, "wt") as f:
            self._write_c_file_header(f)
            self._write_c_file_content(f)

    def _write_c_file_content(self, f: TextIO) -> None:
        # Write "normal" ASCII characters
        for i in range(MIN_GLYPH, MAX_GLYPH + 1):
            if chr(i).islower() and not self.gen_normal:
                continue
            self._write_char_definition(f, chr(i), i)

        # Write nonprintable glyph
        f.write("\n")
        nonprintable = self._get_nonprintable_definition_line()
        f.write(nonprintable)

        # Write array of all glyphs
        if self.gen_normal:
            f.write("\n")
            f.write(
                f"static const uint8_t * const Font_{self._name_style_size}[{MAX_GLYPH} + 1 - {MIN_GLYPH}] = {{\n"
            )
            for i in range(MIN_GLYPH, MAX_GLYPH + 1):
                f.write(f"    Font_{self._name_style_size}_glyph_{i},\n")
            f.write("};\n")

        # Write array of all glyphs for _upper version
        if self.gen_upper:
            f.write("\n")
            f.write(
                f"static const uint8_t * const Font_{self._name_style_size}_upper[{MAX_GLYPH} + 1 - {MIN_GLYPH}] = {{\n"
            )
            for i in range(MIN_GLYPH, MAX_GLYPH + 1):
                comment = ""
                if chr(i).islower():
                    c_from = chr(i)
                    c_to = c_from.upper()
                    i = ord(c_to)
                    comment = f"  // {c_from} -> {c_to}"
                f.write(f"    Font_{self._name_style_size}_glyph_{i},{comment}\n")
            f.write("};\n")

        # Write font info structure
        if self.gen_normal:
            self._write_font_info_structure(f)
        if self.gen_upper:
            self._write_font_info_structure(f, is_upper=True)

    def _write_char_definition(self, f: TextIO, c: str, i: int) -> None:
        self._load_char(c)
        glyph = Glyph.from_face(self.face, c, self.shaveX)
        glyph.print_metrics()
        definition_line = glyph.get_definition_line(self._name_style_size, self.bpp, i)
        f.write(definition_line)

        # Update mix/max metrics
        yMin = glyph.bearingY - glyph.rows
        yMax = yMin + glyph.rows
        self.font_ymin = min(self.font_ymin, yMin)
        self.font_ymax = max(self.font_ymax, yMax)

    def _write_c_file_header(self, f: TextIO) -> None:
        f.write("// This file is generated by core/tools/codegen/gen_font.py\n\n")
        f.write("#include <stdint.h>\n")
        f.write('#include "fonts.h"\n\n')
        f.write("// clang-format off\n\n")
        f.write("// - the first two bytes are width and height of the glyph\n")
        f.write(
            "// - the third, fourth and fifth bytes are advance, bearingX and bearingY of the horizontal metrics of the glyph\n"
        )
        f.write(f"// - the rest is packed {self.bpp}-bit glyph data\n\n")

    # Write font info structure to instantiate font_info_t defined in fonts.h
    def _write_font_info_structure(self, f: TextIO, is_upper: bool = False):
        suffix = "_upper" if is_upper else ""
        f.write("\n")
        f.write(f"const font_info_t Font_{self._name_style_size}{suffix}_info = {{\n")
        f.write(f"    .height = {self.size},\n")
        f.write(f"    .max_height = {self.font_ymax - self.font_ymin},\n")
        f.write(f"    .baseline = {-self.font_ymin},\n")
        f.write(f"    .glyph_data = Font_{self._name_style_size}{suffix},\n")
        f.write(
            f"    .glyph_nonprintable = Font_{self._name_style_size}_glyph_nonprintable,\n"
        )
        f.write("};\n")

    def _get_nonprintable_definition_line(self) -> str:
        c = "?"
        self._load_char(c)
        glyph = Glyph.from_face(self.face, c, self.shaveX, inverse_colors=True)
        return glyph.get_definition_line(
            self._name_style_size, self.bpp, "nonprintable", static=True
        )

    def _load_char(self, c: str) -> None:
        self.face.load_char(c, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL)  # type: ignore

    def _write_h_file(self) -> None:
        with open(OUT_DIR / self._h_file_name, "wt") as f:
            f.write("// This file is generated by core/tools/codegen/gen_font.py\n\n")
            f.write("#include <stdint.h>\n")
            f.write('#include "fonts.h"\n\n')
            f.write(f"#if TREZOR_FONT_BPP != {self.bpp}\n")
            f.write(f"#error Wrong TREZOR_FONT_BPP (expected {self.bpp})\n")
            f.write("#endif\n\n")
            if self.gen_normal:
                f.write(
                    f"extern const font_info_t Font_{self._name_style_size}_info;\n"
                )
            if self.gen_upper:
                f.write(
                    f"extern const font_info_t Font_{self._name_style_size}_upper_info;\n"
                )


if __name__ == "__main__":
    if len(sys.argv) > 1 and "width" in sys.argv[1]:
        WRITE_WIDTHS = True  # type: ignore

    FaceProcessor("Roboto", "Regular", 20).write_files()
    FaceProcessor("Roboto", "Bold", 20).write_files()

    FaceProcessor("TTHoves", "Regular", 21, ext="otf").write_files()
    FaceProcessor("TTHoves", "DemiBold", 21, ext="otf").write_files()
    FaceProcessor(
        "TTHoves", "Bold", 17, ext="otf", gen_normal=False, gen_upper=True
    ).write_files()
    FaceProcessor("RobotoMono", "Medium", 20).write_files()

    # layout caesar
    FaceProcessor(
        "PixelOperator",
        "Regular",
        8,
        bpp=1,
        shaveX=1,
        gen_normal=True,
        gen_upper=True,
    ).write_files()
    FaceProcessor(
        "PixelOperator",
        "Bold",
        8,
        bpp=1,
        shaveX=1,
        gen_normal=True,
        gen_upper=True,
    ).write_files()
    FaceProcessor("PixelOperatorMono", "Regular", 8, bpp=1, shaveX=1).write_files()
    FaceProcessor("Unifont", "Regular", 16, bpp=1, shaveX=1, ext="otf").write_files()
    # NOTE: Unifont Bold does not seem to have czech characters
    FaceProcessor("Unifont", "Bold", 16, bpp=1, shaveX=1, ext="otf").write_files()

    # layout delizia
    FaceProcessor("TTSatoshi", "DemiBold", 42, ext="otf").write_files()
    FaceProcessor("TTSatoshi", "DemiBold", 21, ext="otf").write_files()
    FaceProcessor("TTSatoshi", "DemiBold", 18, ext="otf").write_files()
    FaceProcessor("RobotoMono", "Medium", 21).write_files()
