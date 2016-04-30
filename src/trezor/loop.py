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

DO_NOTHING = const(-5)

evt_handlers = {
    EVT_TSTART: None,
    EVT_TMOVE: None,
    EVT_TEND: None,
    EVT_MSG: None,
}
time_queue = []

if __debug__:
    # For performance stats
    import array
    log_delay_pos = 0
    log_delay_rb_len = const(10)
    log_delay_rb = array.array('i', [0] * log_delay_rb_len)

def __call_at(time, gen):
    if __debug__:
        log.debug(__name__, 'Scheduling %s %s', time, gen)

    if not time:
        time = utime.ticks_us()
    heappush(time_queue, (time, gen))


def __wait_for_gen(gen, cb):
    if isinstance(gen, type_gen):
        ret = yield from gen
    else:
        ret = yield gen
    try:
        cb.throw(StopIteration)
    except Exception as e:
        log.info(__name__, '__wait_gen throw raised %s', e)

    log.info(__name__, '__wait_gen returning %s', ret)


class __Wait():
    pass


def __wait_callback(call_after):
    # TODO: rewrite as instance of __Wait instead of generator
    delegate = yield
    received = 0
    while received < call_after:
        try:
            yield
        except StopIteration:
            received += 1
    __call_at(None, delegate)


def wait_for_first(gens):
    cb = __wait_callback(1)
    for g in gens:
        __call_at(None, __wait_for_gen(g, cb))
    return cb


def wait_for_all(gens):
    cb = __wait_callback(len(gens))
    for g in gens:
        __call_at(None, __wait_for_gen(g, cb))
    return cb


def sleep(us):
    return utime.ticks_us() + us


def run_forever(start_gens):
    if __debug__:
        global log_delay_pos
        global log_delay_rb
        global log_delay_rb_len

    delay_max = const(1000000)

    for gen in start_gens:
        __call_at(None, gen)

    while True:

        if time_queue:
            t, _ = time_queue[0]
            delay = t - utime.ticks_us()
        else:
            delay = delay_max

        if __debug__:
            # Adding current delay to ring buffer for performance stats
            log_delay_rb[log_delay_pos] = delay
            log_delay_pos = (log_delay_pos + 1) % log_delay_rb_len

        event = msg.select(delay)

        if event:
            # run interrupt handler
            log.info(__name__, "Received data: %s", event)
            continue
        else:
            # run something from the time queue
            _, gen = heappop(time_queue)

        try:
            ret = gen.send(None)

        except StopIteration as e:
            log.info(__name__, '%s ended', gen)
            # gen ended, forget it and go on
            continue

        except Exception as e:
            log.exception(__name__, e)
            continue

        if isinstance(ret, int):
            if ret >= 0:
                # sleep until ret, call us later
                __call_at(ret, gen)
            else:
                # wait for event
                raise NotImplementedError()

        elif isinstance(ret, type_gen):
            log.info(__name__, 'Scheduling %s -> %s', gen, ret)
            ret.send(None)
            ret.send(gen)

        elif ret is None:
            # just call us asap
            __call_at(None, gen)

        else:
            raise Exception("Unhandled result %s by %s" % (ret, gen))
