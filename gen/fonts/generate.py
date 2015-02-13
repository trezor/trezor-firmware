#!/usr/bin/python
from PIL import Image

class Img(object):

    def __init__(self, fn):
        im = Image.open(fn)
        self.w, self.h = im.size
        self.data = list(im.getdata())

    def pixel(self, r, c):
        p = self.data[ r + c * self.w ]
        if p == (255, 255, 255):
            return '0'
        if p == (0, 0, 0):
            return '1'
        if p == (255, 0, 255):
            return None
        raise Exception('Unknown color', p)

img = Img('font.png')
cur = ''
idx = 0

for i in range(img.w):
    if img.pixel(i, 0) == None:
        cur = '\\x%02x' % (len(cur) / 4) + cur
        ch = chr(idx) if idx >= 32 and idx <= 126 else '_'
        print '\t/* 0x%02x %c */ (uint8_t *)"%s",' % (idx, ch , cur)
        cur = ''
        idx += 1
        continue
    val = img.pixel(i, 0) + img.pixel(i, 1) + img.pixel(i, 2) + img.pixel(i, 3) + img.pixel(i, 4) + img.pixel(i, 5) + img.pixel(i, 6) + img.pixel(i, 7)
    cur += '\\x%02x' % int(val, 2)
