import sys
sys.path.append('lib')

import gc

from trezor import loop
from trezor import workflow
from trezor import log

log.level = log.DEBUG
# log.level = log.INFO


def perf_info_debug():
    while True:
        queue_len = len(loop._scheduled_tasks)

        delay_avg = sum(loop.log_delay_rb) / loop.log_delay_rb_len
        delay_last = loop.log_delay_rb[loop.log_delay_pos]

        mem_alloc = gc.mem_alloc()
        gc.collect()
        log.debug(__name__, "mem_alloc: %s/%s, delay_avg: %d, delay_last: %d, queue_len: %d",
                  mem_alloc, gc.mem_alloc(), delay_avg, delay_last, queue_len)

        yield loop.Sleep(1000000)


def perf_info():
    while True:
        gc.collect()
        log.info(__name__, "mem_alloc: %d", gc.mem_alloc())
        yield loop.Sleep(1000000)


def run(default_workflow):
    # if __debug__:
    #     loop.schedule_task(perf_info_debug())
    # else:
    #     loop.schedule_task(perf_info())
    workflow.start_default(default_workflow)
    loop.run_forever()
