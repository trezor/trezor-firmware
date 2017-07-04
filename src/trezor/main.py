import gc
import micropython
import sys

sys.path.append('lib')

from trezor import loop
from trezor import workflow
from trezor import log

log.level = log.DEBUG


def perf_info():
    prev = 0
    peak = 0
    sleep = loop.sleep(100000)
    while True:
        gc.collect()
        used = gc.mem_alloc()
        if used != prev:
            prev = used
            peak = max(peak, used)
            print('peak %d, used %d' % (peak, used))
        yield sleep


def run(default_workflow):
    # loop.schedule_task(perf_info())
    workflow.start_default(default_workflow)
    loop.run_forever()
