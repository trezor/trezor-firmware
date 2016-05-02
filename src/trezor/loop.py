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

class Wait():
    def __init__(self, gens, wait_for=1, exit_others=True):
        self.wait_for = wait_for
        self.exit_others = exit_others
        self.received = 0
        self.callback = None
        self.gens = gens

        for g in gens:
            __call_at(None, self._wait(g))

    def _wait(self, gen):
        if isinstance(gen, type_gen):
            ret = yield from gen
        else:
            ret = yield gen

        self.finish(gen, ret)

    def finish(self, gen, result):
        self.received += 1

        if self.received == self.wait_for:
            __call_at(None, self.callback)
            self.callback = None

            if self.exit_others:
                for g in self.gens:
                    try:
                        g.throw(StopIteration())
                    except:
                        pass

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

        elif isinstance(ret, Wait):
            log.info(__name__, 'Scheduling %s -> %s', gen, ret)
            ret.callback = gen

        elif ret is None:
            # just call us asap
            __call_at(None, gen)

        else:
            raise Exception("Unhandled result %s by %s" % (ret, gen))
