import usb

usb.bus.open()

import trezorio as io
from trezorui import Display

d = Display()

d.clear()
d.backlight(255)

i = 0

while True:
    d.print('Loop %d\n' % i)
    i += 1
    r = [0, 0]
    if io.poll([io.TOUCH], r, 1000000):
        print('TOUCH', r)
    else:
        print('NOTOUCH')
