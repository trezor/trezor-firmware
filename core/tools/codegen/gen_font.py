#!/usr/bin/env python3

# script used to generate /embed/extmod/modtrezorui/font_*_*.c

from __future__ import annotations

from pathlib import Path

import freetype

HERE = Path(__file__).parent
FONTS_DIR = HERE / "fonts"

MIN_GLYPH = ord(" ")
MAX_GLYPH = ord("~")

# metrics explanation: https://www.freetype.org/freetype2/docs/glyphs/metrics.png


def process_bitmap_buffer(buf: list[int], bpp: int) -> list[int]:
    res = buf[:]
    if bpp == 1:
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
        for _ in range(4 - len(res) % 4):
            res.append(0)
        res = [
            ((a & 0xC0) | ((b & 0xC0) >> 2) | ((c & 0xC0) >> 4) | ((d & 0xC0) >> 6))
            for a, b, c, d in [res[i : i + 4] for i in range(0, len(res), 4)]
        ]
    elif bpp == 4:
        if len(res) % 2 > 0:
            res.append(0)
        res = [
            ((a & 0xF0) | (b >> 4))
            for a, b in [res[i : i + 2] for i in range(0, len(res), 2)]
        ]
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


def process_face(
    name: str,
    style: str,
    size: int,
    bpp: int = 4,
    shaveX: int = 0,
    ext: str = "ttf",
) -> None:
    print("Processing ... %s %s %s" % (name, style, size))
    file_name = FONTS_DIR / f"{name}-{style}.{ext}"
    face = freetype.Face(str(file_name))
    face.set_pixel_sizes(0, size)
    fontname = "%s_%s_%d" % (name.lower(), style.lower(), size)
    font_ymin = 0
    font_ymax = 0

    with open("font_%s.c" % fontname, "wt") as f:
        f.write("#include <stdint.h>\n\n")
        f.write("// clang-format off\n\n")
        f.write("// - the first two bytes are width and height of the glyph\n")
        f.write(
            "// - the third, fourth and fifth bytes are advance, bearingX and bearingY of the horizontal metrics of the glyph\n"
        )
        f.write("// - the rest is packed %d-bit glyph data\n\n" % bpp)
        for i in range(MIN_GLYPH, MAX_GLYPH + 1):
            c = chr(i)
            face.load_char(c, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL)
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
            # the following code is here just for some letters (listed below)
            # not using negative bearingX makes life so much easier; add it to advance instead
            if bearingX < 0:
                if c in "AXYjxy}),/_":
                    advance += -bearingX
                    bearingX = 0
                else:
                    raise ValueError("Negative bearingX for character '%s'" % c)
            bearingY = metrics.horiBearingY // 64
            assert advance >= 0 and advance <= 255
            assert bearingX >= 0 and bearingX <= 255
            if bearingY < 0:  # HACK
                print("normalizing bearingY %d for '%s'" % (bearingY, c))
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
                print(
                    'Glyph "%c": removed %d pixel columns from the left'
                    % (c, remove_left)
                )
            print(
                'Loaded glyph "%c" ... %d x %d @ %d grays (%d bytes, metrics: %d, %d, %d)'
                % (
                    c,
                    bitmap.width,
                    bitmap.rows,
                    bitmap.num_grays,
                    len(bitmap.buffer),
                    advance,
                    bearingX,
                    bearingY,
                )
            )
            f.write(
                "/* %c */ static const uint8_t Font_%s_%s_%d_glyph_%d[] = { %d, %d, %d, %d, %d"
                % (c, name, style, size, i, width, rows, advance, bearingX, bearingY)
            )
            if len(buf) > 0:
                f.write(
                    ", "
                    + ", ".join(["%d" % x for x in process_bitmap_buffer(buf, bpp)])
                )
            f.write(" };\n")

            if i == ord("?"):
                nonprintable = (
                    "\nconst uint8_t Font_%s_%s_%d_glyph_nonprintable[] = { %d, %d, %d, %d, %d"
                    % (name, style, size, width, rows, advance, bearingX, bearingY)
                )
                nonprintable += ", " + ", ".join(
                    ["%d" % (x ^ 0xFF) for x in process_bitmap_buffer(buf, bpp)]
                )
                nonprintable += " };\n"

            yMin = bearingY - rows
            yMax = yMin + rows
            font_ymin = min(font_ymin, yMin)
            font_ymax = max(font_ymax, yMax)

        f.write(nonprintable)

        f.write(
            "\nconst uint8_t * const Font_%s_%s_%d[%d + 1 - %d] = {\n"
            % (name, style, size, MAX_GLYPH, MIN_GLYPH)
        )
        for i in range(MIN_GLYPH, MAX_GLYPH + 1):
            f.write("    Font_%s_%s_%d_glyph_%d,\n" % (name, style, size, i))
        f.write("};\n")

    with open("font_%s.h" % fontname, "wt") as f:
        f.write("#include <stdint.h>\n\n")
        f.write("#if TREZOR_FONT_BPP != %d\n" % bpp)
        f.write("#error Wrong TREZOR_FONT_BPP (expected %d)\n" % bpp)
        f.write("#endif\n")

        f.write("#define Font_%s_%s_%d_HEIGHT %d\n" % (name, style, size, size))
        f.write(
            "#define Font_%s_%s_%d_MAX_HEIGHT %d\n"
            % (name, style, size, font_ymax - font_ymin)
        )
        f.write("#define Font_%s_%s_%d_BASELINE %d\n" % (name, style, size, -font_ymin))
        f.write(
            "extern const uint8_t* const Font_%s_%s_%d[%d + 1 - %d];\n"
            % (name, style, size, MAX_GLYPH, MIN_GLYPH)
        )
        f.write(
            "extern const uint8_t Font_%s_%s_%d_glyph_nonprintable[];\n"
            % (name, style, size)
        )


process_face("Roboto", "Regular", 20)
process_face("Roboto", "Bold", 20)

process_face("TTHoves", "Regular", 21, ext="otf")
process_face("TTHoves", "DemiBold", 21, ext="otf")
process_face("TTHoves", "Bold", 17, ext="otf")
process_face("RobotoMono", "Medium", 20)

process_face("PixelOperator", "Regular", 8, bpp=1, shaveX=1)
process_face("PixelOperator", "Bold", 8, bpp=1, shaveX=1)
process_face("PixelOperatorMono", "Regular", 8, bpp=1, shaveX=1)

# For model R
process_face("Unifont", "Regular", 16, bpp=1, shaveX=1, ext="otf")
process_face("Unifont", "Bold", 16, bpp=1, shaveX=1, ext="otf")
