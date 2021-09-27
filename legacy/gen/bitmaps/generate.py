#!/usr/bin/env python3
import glob
import os

from PIL import Image

hdrs = []
data = []
imgs = []


def encode_pixels(img):
    r = ""
    img = ["1" if x >= 128 else "0" for x in img]
    for i in range(len(img) // 8):
        c = "".join(img[i * 8 : i * 8 + 8])
        r += "0x%02x, " % int(c, 2)
    return r


cnt = 0
for fn in sorted(glob.glob("*.png")):
    print("Processing:", fn)
    im = Image.open(fn)
    name = os.path.splitext(fn)[0]
    w, h = im.size
    if w % 8 != 0:
        raise Exception(f"Width must be divisible by 8! ({fn} is {w}x{h})")
    img = list(im.getdata())
    hdrs.append(f"extern const BITMAP bmp_{name};\n")
    imgs.append(f"const BITMAP bmp_{name} = {{{w}, {h}, bmp_{name}_data}};\n")
    data.append(f"const uint8_t bmp_{name}_data[] = {{ {encode_pixels(img)}}};\n")
    cnt += 1

with open("../bitmaps.c", "wt") as f:
    f.write("// clang-format off\n")
    f.write('#include "bitmaps.h"\n\n')
    for i in range(cnt):
        f.write(data[i])
    f.write("\n")
    for i in range(cnt):
        f.write(imgs[i])
    f.close()

with open("../bitmaps.h", "wt") as f:
    f.write(
        """#ifndef __BITMAPS_H__
#define __BITMAPS_H__

#include <stdint.h>

typedef struct {
  uint8_t width, height;
  const uint8_t *data;
} BITMAP;

"""
    )

    for i in range(cnt):
        f.write(hdrs[i])

    f.write("\n#endif\n")
    f.close()
