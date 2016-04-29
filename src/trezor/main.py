import sys
sys.path.append('lib')

import gc

from trezor import loop
from trezor import layout

if __debug__:
    import logging
    logging.basicConfig(level=logging.INFO)

def perf_info_debug():
    while True:
        queue = [str(x[2]).split("'")[1] for x in loop.q]

        delay_avg = sum(loop.log_delay_rb) / loop.log_delay_rb_len
        delay_last = loop.log_delay_rb[loop.log_delay_pos]

        mem_alloc = gc.mem_alloc()
        gc.collect()
        print("mem_alloc: %s/%s, delay_avg: %d, delay_last: %d, queue: %s" % \
              (mem_alloc, gc.mem_alloc(), delay_avg, delay_last, ', '.join(queue)))

        yield loop.Sleep(1000000)

def perf_info():
    while True:
        gc.collect()
        print("mem_alloc: %d" % gc.mem_alloc())
        yield loop.Sleep(1000000)

def run(main_layout):
    if __debug__:
        loop.call_soon(perf_info_debug())
    else:
        loop.call_soon(perf_info())

    loop.call_soon(layout.set_main(main_layout))

    loop.run_forever()
    loop.close()
