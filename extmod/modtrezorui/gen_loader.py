#!/usr/bin/python3
import math
import sys

outer = 83
inner = 55

print('static const int img_loader_size = %d;' % outer)
print('static const uint16_t img_loader[%d][%d] = {' % (outer, outer))
for y in range(outer):
    print('    {', end='')
    for x in range(outer):
        d = math.sqrt((outer - 1 - x) ** 2 + (outer - 1 - y) ** 2)
        c = {}
        for i in [5, 15]:
            if (inner - 0.5 <= d) and (d <= inner + 0.5):
                c[i] = 15 * (d - inner + 0.5);
            elif (inner + 0.5 <= d) and (d <= inner + 1.5):
                c[i] = 15
            elif (inner + 1.5 <= d) and (d <= inner + 2.5):
                c[i] = 15 if i == 15 else 15 - (15 - i) * (d - inner - 1.5)
            elif (outer - 1.5 <= d) and (d <= outer - 0.5):
                c[i] = i - i * (d - outer + 1.5)
            elif (inner + 2.5 < d) and (d < outer - 1.5):
                c[i] = i
            else:
                c[i] = 0
            # clamp (should not be needed)
            c[i] = max(0, min(int(c[i]), 15))
        a = int(math.atan2((outer - 1 - x), (outer - 1 - y)) * 2 * 249 / math.pi)
        v = (a << 8) | (c[15] << 4) | c[5]
        print('%d,' % v, end='')
    print('},')
print('};')
