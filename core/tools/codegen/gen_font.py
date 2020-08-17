#!/usr/bin/env python3

# script used to generate /embed/extmod/modtrezorui/font_*_*.c


import freetype

MIN_GLYPH = ord(" ")
MAX_GLYPH = ord("~")

# metrics explanation: https://www.freetype.org/freetype2/docs/glyphs/metrics.png


def process_bitmap_buffer(buf, bpp):
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


def process_face(name, style, size, bpp=4, shave_bearingX=0):
    print("Processing ... %s %s %s" % (name, style, size))
    face = freetype.Face("fonts/%s-%s.ttf" % (name, style))
    face.set_pixel_sizes(0, size)
    fontname = "%s_%s_%d" % (name.lower(), style.lower(), size)
    with open("font_%s.h" % fontname, "wt") as f:
        f.write("#include <stdint.h>\n\n")
        f.write("#if TREZOR_FONT_BPP != %d\n" % bpp)
        f.write("#error Wrong TREZOR_FONT_BPP (expected %d)\n" % bpp)
        f.write("#endif\n")
        f.write(
            "extern const uint8_t* const Font_%s_%s_%d[%d + 1 - %d];\n"
            % (name, style, size, MAX_GLYPH, MIN_GLYPH)
        )
        f.write(
            "extern const uint8_t Font_%s_%s_%d_glyph_nonprintable[];\n"
            % (name, style, size)
        )
    with open("font_%s.c" % fontname, "wt") as f:
        f.write("#include <stdint.h>\n\n")
        f.write("// clang-format off\n\n")
        f.write("// - the first two bytes are width and height of the glyph\n")
        f.write("// - the third, fourth and fifth bytes are advance, bearingX and bearingY of the horizontal metrics of the glyph\n")
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
            # discard space on the left side
            if shave_bearingX > 0:
                advance -= min(advance, bearingX, shave_bearingX)
                bearingX -= min(advance, bearingX, shave_bearingX)
            # the following code is here just for some letters (listed below)
            # not using negative bearingX makes life so much easier; add it to advance instead
            if c in "jy}),/" and bearingX < 0:
                advance += -bearingX
                bearingX = 0
            bearingY = metrics.horiBearingY // 64
            assert advance >= 0 and advance <= 255
            assert bearingX >= 0 and bearingX <= 255
            assert bearingY >= 0 and bearingY <= 255
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
            buf = list(bitmap.buffer)
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

        f.write(nonprintable)

        f.write(
            "\nconst uint8_t * const Font_%s_%s_%d[%d + 1 - %d] = {\n"
            % (name, style, size, MAX_GLYPH, MIN_GLYPH)
        )
        for i in range(MIN_GLYPH, MAX_GLYPH + 1):
            f.write("    Font_%s_%s_%d_glyph_%d,\n" % (name, style, size, i))
        f.write("};\n")


process_face("Roboto", "Regular", 20)
process_face("Roboto", "Bold", 20)
process_face("RobotoMono", "Regular", 20)

process_face("PixelOperator", "Regular", 8, 1, 1)
process_face("PixelOperator", "Bold", 8, 1, 1)
process_face("PixelOperatorMono", "Regular", 8, 1, 1)
