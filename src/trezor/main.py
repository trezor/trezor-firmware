import sys
sys.path.append('lib')

import gc

from trezor import loop
from trezor import layout

if __debug__:
    import logging
    logging.basicConfig(level=logging.INFO)

def perf_info():
    while True:
        queue = [str(x[2]).split("'")[1] for x in loop.q]
        mem_alloc = gc.mem_alloc()
        gc.collect()
        print("mem_alloc: %s/%s, last_sleep: %d, queue: %s" % \
              (mem_alloc, gc.mem_alloc(), loop.last_sleep, ', '.join(queue)))

        yield loop.Sleep(1000000)

_main_layout = None

def run(main_layout):
    # ui.touch.start(lambda x, y: print('touch start %d %d\n' % (x, y)))
    # ui.touch.move(lambda x, y: print('touch move %d %d\n' % (x, y)))
    # ui.touch.end(lambda x, y: print('touch end %d %d\n' % (x, y)))

    if __debug__:
        loop.call_soon(perf_info())

    global _main_layout
    _main_layout = main_layout
    loop.call_soon(layout.set_main(_main_layout))

    loop.run_forever()
    loop.close()
