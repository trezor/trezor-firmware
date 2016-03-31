# import time
import sys
sys.path.append('lib')

import gc
import utime
import logging
# import uasyncio
import math
from uasyncio import core

from TrezorUi import Display

from trezor import ui

from . import utils

d = Display()
logging.basicConfig(level=logging.INFO)
loop = core.get_event_loop()

def meminfo():
    mem_free = gc.mem_free()
    collected = gc.collect()
    print("free_mem: %s/%s, collect: %s" % (mem_free, gc.mem_free(), collected))
    loop.call_later(1, meminfo)

def animate():
    col = 0
    f = open('../assets/lock.toi', 'r')

    while True:
        col %= 0xff
        col += 0x0f

        d.icon(190, 170, f.read(), utils.rgb2color(col, 0, 0), 0xffff)
        f.seek(0)

        yield from core.sleep(0.5)

sec = 0
event = None
def sekunda(x):
    global sec
    print('Sekunda %d' % sec)
    

    if sec == 0:
        # if loop.button_cb:
        #    loop.call_soon(loop.button_cb, 'levy')
        #    loop.button_cb = None
        return

    sec += 1
    loop.call_later(1, sekunda, x)

def wait_for():
    print("Jsem tady")

    ktery = yield core.IOButton()
    print(ktery)
    
    print("Po cekani na event")

def tap_to_confirm():
    STEP_X = 0.07
    DELAY = 0.01
    BASE_COLOR = (0x00, 0x00, 0x00)
    MIN_COLOR = 0x00
    MAX_COLOR = 0xB0

    _background = utils.rgb2color(255, 255, 255)
    x = math.pi
    while True:
        x += STEP_X
        if x > 2 * math.pi:
            x -= 2 * math.pi
        y = 1 + math.sin(x)
        
        # Normalize color from interval 0:2 to MIN_COLOR:MAX_COLOR
        col = int((MAX_COLOR - MIN_COLOR) / 2 * y) + MIN_COLOR
        foreground = utils.rgb2color(BASE_COLOR[0] + col, BASE_COLOR[1] + col, BASE_COLOR[2] + col)

        ui.display.text(10, 220, 'TAP TO CONFIRM', 2, foreground, _background)

        yield from core.sleep(DELAY)

def run():
    # sekunda(3)
    # loop.call_soon(wait_for())

    loop.call_soon(meminfo)
    loop.call_soon(tap_to_confirm())
    loop.call_soon(animate())

    loop.run_forever()
    loop.close()
