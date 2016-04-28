# import time
import sys
sys.path.append('lib')

if sys.platform == 'linux':
    # Packages used only on linux platform (named pipes, ...)
    sys.path.append('lib_linux')

import utime
import math
import gc

from uasyncio import core
# import transport_pipe as pipe

from trezor import ui
from trezor import msg
from trezor.utils import unimport
from trezor import layout

logging.basicConfig(level=logging.INFO)
loop = core.get_event_loop()

def perf_info():
    mem_alloc = gc.mem_alloc()
    gc.collect()
    print("mem_alloc: %s/%s, last_sleep: %d" % \
          (mem_alloc, gc.mem_alloc(), loop.last_sleep))
    loop.call_later(1000000, perf_info)

def animate():
    col = 0
    # hawcons gesture
    f = open('playground/tap_64.toig', 'r')

    while True:
        col %= 0xff
        col += 0x0f

        ui.display.icon(190, 170, f.read(), ui.rgbcolor(col, 0, 0), 0xffff)
        f.seek(0)

        yield core.Sleep(int(0.5 * 1000000))

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
    DELAY = int(0.01 * 1000000)
    BASE_COLOR = (0x00, 0x00, 0x00)
    MIN_COLOR = 0x00
    MAX_COLOR = 0xB0

    f = open('playground/tap_64.toig', 'r')

    _background = ui.rgbcolor(255, 255, 255)
    x = math.pi
    while True:
        x += STEP_X
        if x > 2 * math.pi:
            x -= 2 * math.pi
        y = 1 + math.sin(x)
        
        # ui.display.bar(0, 170, 240, 70, _background)

        # Normalize color from interval 0:2 to MIN_COLOR:MAX_COLOR
        col = int((MAX_COLOR - MIN_COLOR) / 2 * y) + MIN_COLOR
        foreground = ui.rgbcolor(BASE_COLOR[0] + col, BASE_COLOR[1] + col, BASE_COLOR[2] + col)

        ui.display.text(68, 212, 'TAP TO CONFIRM', 2, foreground, _background)

        f.seek(0)
        ui.display.icon(3, 170, f.read(), _background, foreground)
        # ui.display.icon(165, 50, f.read(), _background, foreground)

        try:
            yield core.Sleep(DELAY)
        except StopIteration:
            print("Somebody asked me to stop layout tap_to_confirm")
            return

def on_read():
    print("READY TO READ")
    print(msg.read())

@unimport
def zprava():
    from _io import BytesIO

    from trezor.messages.GetAddress import GetAddress

    m = GetAddress()
    m.address_n = [1, 2, 3]
    m.show_display = True

    print(m.__dict__)
    f = BytesIO()
    m.dump(f)
    data = f.getvalue()
    f.close()
    print(data)
    # m2 = GetAddress.load(BytesIO(data))
    # print(m2.__dict__)

def novy_layout():
    print("Novy layout!")
    yield core.Sleep(2 * 1000000)
    return tap_to_confirm

def run():
    # pipe.init('../pipe', on_read)
    # msg.set_notify(on_read)

    zprava()
    
    loop.call_soon(perf_info)
    loop.call_soon(layout.set_main_layout(tap_to_confirm))

    loop.call_later(2 * 1000000, layout.change_layout(novy_layout))
    # loop.call_soon(animate())

    loop.run_forever()
    loop.close()
