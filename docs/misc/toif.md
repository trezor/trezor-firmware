# Trezor Optimized Image Format (TOIF)

All multibyte integer values are little endian!

## Header

| offset | length | name | description |
|-------:|-------:|------|-------------|
| 0x0000 | 3      | magic | `TOI` |
| 0x0003 | 1      | fmt | data format: `f` or `g` (see below) |
| 0x0004 | 2      | width | width of the image |
| 0x0006 | 2      | height | height of the image |
| 0x0008 | 4      | datasize | length of the compressed data |
| 0x000A | ?      | data | compressed data (see below) |

## Format

TOI currently supports 2 variants:

* `f`: full-color
* `g`: gray-scale

### Full-color

For each pixel a 16-bit value is used.
First 5 bits are used for red component, next 6 bits are green,
final 5 bits are blue:

| 15 | 14 | 13 | 12 | 11 | 10 | 9 | 8 | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |
|----|----|----|----|----|----|---|---|---|---|---|---|---|---|---|---|
| R | R | R | R | R | G | G | G | G | G | G | B | B | B | B | B |

### Gray-scale

Each pixel is encoded using a 4-bit value.
Each byte contains color of two pixels:

| 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |
|---|---|---|---|---|---|---|---|
| Po | Po | Po | Po | Pe | Pe | Pe | Pe |

Where Po is odd pixel and Pe is even pixel.

## Compression

Pixel data is compressed using DEFLATE algorithm with 10-bit sliding window
and no header. This can be achieved with ZLIB library by using the following:

```python
import zlib
z = zlib.compressobj(level=9, wbits=-10)
zdata = z.compress(pixeldata) + z.flush()
```

## Tools

* [toif_convert](../tools/toif_convert.py) - tool for converting PNGs into TOI format and back
