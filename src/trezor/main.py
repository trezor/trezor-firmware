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

def run(main_layout):
    if __debug__:
        loop.call_soon(perf_info())

    loop.call_soon(layout.set_main(main_layout))

    loop.run_forever()
    loop.close()
