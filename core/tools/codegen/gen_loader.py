#!/usr/bin/env python3

# script used to generate /embed/upymod/modtrezorui/loader_X.h

import math


def gen_loader(model: str, outer: int, inner: int) -> None:
    with open(f"loader_{model}.h", "wt") as f:
        f.write("// clang-format off\n")
        f.write(f"static const int img_loader_size = {outer};\n" % outer)
        f.write(f"static const uint16_t img_loader[{outer}][{outer}] = {{\n")
        for y in range(outer):
            f.write("    {")
            for x in range(outer):
                d = math.sqrt((outer - 1 - x) ** 2 + (outer - 1 - y) ** 2)
                c = {}
                for i in [5, 15]:
                    if inner - 0.5 <= d <= inner + 0.5:
                        c[i] = 15 * (d - inner + 0.5)
                    elif inner + 0.5 <= d <= inner + 1.5:
                        c[i] = 15
                    elif inner + 1.5 <= d <= inner + 2.5:
                        c[i] = 15 if i == 15 else 15 - (15 - i) * (d - inner - 1.5)
                    elif outer - 1.5 <= d <= outer - 0.5:
                        c[i] = i - i * (d - outer + 1.5)
                    elif inner + 2.5 < d < outer - 1.5:
                        c[i] = i
                    else:
                        c[i] = 0
                    # clamp (should not be needed)
                    c[i] = max(0, min(int(c[i]), 15))
                a = int(
                    math.atan2((outer - 1 - x), (outer - 1 - y)) * 2 * 249 / math.pi
                )
                v = (a << 8) | (c[15] << 4) | c[5]
                f.write(f"{v},")
            f.write("},\n")
        f.write("};\n")


if __name__ == "__main__":
    gen_loader("T", 60, 42)
    gen_loader("R", 20, 14)
