#!/usr/bin/env python3
from PIL import Image


class Img(object):
    def __init__(self, fn):
        im = Image.open(fn)
        self.w, self.h = im.size
        self.data = list(im.getdata())

    def pixel(self, r, c):
        p = self.data[r + c * self.w]
        if p == (255, 255, 255):
            return "0"
        if p == (0, 0, 0):
            return "1"
        if p == (255, 0, 255):
            return None
        raise Exception("Unknown color", p)


def convert(imgfile, outfile):
    img = Img(imgfile)
    cur = ""
    with open(outfile, "w") as f:
        for i in range(128 - 32):
            x = (i % 16) * 10
            y = (i // 16) * 10
            cur = ""
            while img.pixel(x, y) is not None:
                val = "".join(img.pixel(x, y + j) for j in range(8))
                x += 1
                cur += "\\x%02x" % int(val, 2)
            cur = "\\x%02x" % (len(cur) // 4) + cur
            i += 32
            ch = "_" if (i == 127) else chr(i)
            f.write('\t/* 0x%02x %c */ (uint8_t *)"%s",\n' % (i, ch, cur))


convert("fonts/fontfixed.png", "fontfixed.inc")
convert("fonts/font.png", "font.inc")
