#!/usr/bin/env python3
import glob
import os

from PIL import Image

hdrs = []
data = []
imgs = []


def encode_pixels(img):
    r = ""
    img = [(x[0] + x[1] + x[2] > 384 and "0" or "1") for x in img]
    for i in range(len(img) // 8):
        c = "".join(img[i * 8 : i * 8 + 8])
        r += "0x%02x, " % int(c, 2)
    return r


cnt = 0
for fn in sorted(glob.glob("*.png")):
    print("Processing:", fn)
    im = Image.open(fn)
    print("mode:", im.mode)
    name = os.path.splitext(fn)[0]
    w, h = im.size
    print("picture size ", name, w, h)
    #   if w % 8 != 0:
    #   raise Exception("Width must be divisable by 8! (%s is %dx%d)" % (fn, w, h))
    img = list(im.getdata())
    hdrs.append("extern const BITMAP bmp_%s;\n" % name)
    imgs.append("const BITMAP bmp_%s = {%d, %d, bmp_%s_data};\n" % (name, w, h, name))
    data.append("const uint8_t bmp_%s_data[] = { %s};\n" % (name, encode_pixels(img)))
    cnt += 1

with open("../prompt.c", "wt") as f:
    f.write("// clang-format off\n")
    f.write('#include "prompt.h"\n\n')
    for i in range(cnt):
        f.write(data[i])
    f.write("\n")
    for i in range(cnt):
        f.write(imgs[i])
    f.close()

with open("../prompt.h", "wt") as f:
    f.write(
        """#ifndef __PROMPT_H__
#define __PROMPT_H__

#include <stdint.h>

#include "bitmaps.h"

#define LOGO_WIDTH 8
#define LOGO_HEIGHT 8

"""
    )

    for i in range(cnt):
        f.write(hdrs[i])

    f.write("\n#endif\n")
    f.close()
