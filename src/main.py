from TrezorUi import Display

def rgb2color(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | ((b & 0xF8) >> 3)

BLACK = 0x0000
WHITE = 0xFFFF
BLUEGRAY = rgb2color(0x80, 0x80, 0x80)

d = Display()

d.bar(0, 0, 240, 40, BLUEGRAY)
d.bar(0, 40, 240, 200, WHITE)

d.text(10, 28, 'Sending', 2, WHITE, BLUEGRAY)

d.text(10, 80, '110.126967 BTC', 2, BLACK, WHITE)
d.text(10, 110, 'to this address:', 1, BLACK, WHITE)

d.text(10, 140, '1BitkeyP2nDd5oa64x', 0, BLACK, WHITE)
d.text(10, 160, '7AjvBbbwST54W5Zmx2', 0, BLACK, WHITE)


while True:
    pass
