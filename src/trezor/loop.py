import utime

from uheapq import heappop, heappush
from .utils import type_gen
from . import msg
from . import ui
from . import log

EVT_TSTART = const(-1)
EVT_TMOVE = const(-2)
EVT_TEND = const(-3)
EVT_MSG = const(-4)

evt_handlers = { EVT_TSTART: None,
                 EVT_TMOVE: None,
                 EVT_TEND: None,
                 EVT_MSG: None, }
time_queue = []

if __debug__:
    # For performance stats
    import array
    log_delay_pos = 0
    log_delay_rb_len = const(10)
    log_delay_rb = array.array('i', [0] * log_delay_rb_len)


def __wait_for_event(timeout_us):
    if __debug__:
        # Adding delay to ring buffer for performance stats
        global log_delay_pos
        global log_delay_rb
        global log_delay_rb_len
        log_delay_rb[log_delay_pos] = timeout_us
        log_delay_pos = (log_delay_pos + 1) % log_delay_rb_len

    event = msg.select(timeout_us)
    if event:
        # print('msg:', m)
        # utime.sleep_us(10000)
        if event[0] == 2:
            ui.display.bar(event[1], event[2], 2, 2, ui.BLACK)
    return event


def __call_at(time, gen, *args):
    if __debug__:
        log.debug(__name__, 'Scheduling %s %s %s', time, gen, args)

    if not time:
        time = utime.ticks_us()
    heappush(time_queue, (time, gen, args))


def sleep(us):
    return utime.ticks_us() + us


def run_forever(start_gens):
    delay_max = const(1000000)

    for gen in start_gens:
        __call_at(None, gen)

    while True:

        if time_queue:
            t, _, _ = time_queue[0]
            delay = t - utime.ticks_us()
        else:
            delay = delay_max

        event = __wait_for_event(delay)

        if event:
            # run interrupt handler
            raise NotImplementedError()
        else:
            # run something from the time queue
            _, gen, args = heappop(time_queue)

        try:
            if not args:
                args = (None,)
            ret = gen.send(*args)
        except StopIteration as e:
            # gen ended, forget it and go on
            continue

        if isinstance(ret, type_gen):
            # generator, run it and call us asap
            __call_at(None, ret)
            __call_at(None, gen, *args)

        elif isinstance(ret, int):
            if ret >= 0:
                # sleep until ret, call us later
                __call_at(ret, gen, *args)
            else:
                # wait for event
                raise NotImplementedError()

        elif ret is None:
            # just call us asap
            __call_at(None, gen, *args)
