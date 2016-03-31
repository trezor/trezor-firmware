# import time
import gc
import utime
import logging
import uasyncio
from uasyncio import core

from TrezorUi import Display

from . import utils

d = Display()
logging.basicConfig(level=logging.INFO)
loop = uasyncio.get_event_loop()

if __debug__:
    def meminfo():
        mem_free = gc.mem_free()
        gc.collect()
        print("free_mem: %s/%s, collect: %s" % (mem_free, gc.mem_free(), gc.collect()))
        loop.call_later(1, meminfo)

    # meminfo()

def animate(col):

    col %= 0xff
    col += 0x0f

    f = open('../assets/lock.toi', 'r')
    d.icon(10, 170, f.read(), utils.rgb2color(0, col, 0), 0xffff)

    loop.call_later(0.5, animate, col)

def animate2(col):

    col %= 0xff
    col += 0x0f

    # yield True
    f = open('../assets/lock.toi', 'r')
    d.icon(170, 170, f.read(), utils.rgb2color(col, 0, 0), 0xffff)

    loop.call_later(0.1, animate2, col)

sec = 0
event = None
def sekunda(x):
    global sec
    print('Sekunda %d' % sec)
    

    if sec == x:
        loop.call_soon(loop.button_cb, 'levy')
        loop.button_cb = None

    sec += 1
    loop.call_later(1, sekunda, x)


    # global event
    # event = wait_for()
    # event.__next__()


def wait_for():
    print("Jsem tady")

    ktery = yield core.IOButton()
    print(ktery)
    
    print("Po cekani na event")

def run():
    '''
    d = Display()
    d.bar(0, 0, 240, 240, 0)

    f = open('../assets/trezor.toi', 'r')
    d.image(0, 0, f.read())
    '''

    # logging.basicConfig(level=logging.INFO)

    sekunda(3)

    loop.call_soon(animate, 0x0000)
    loop.call_soon(animate2, 0x00ff)
    
    loop.call_soon(wait_for())
    
    loop.run_forever()
    loop.close()
