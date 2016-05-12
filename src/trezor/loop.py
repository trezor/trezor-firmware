import utime

from uheapq import heappop, heappush
from .utils import type_gen
from . import msg
from . import log

if __debug__:
    # For performance stats
    import array
    log_delay_pos = 0
    log_delay_rb_len = const(10)
    log_delay_rb = array.array('i', [0] * log_delay_rb_len)

TOUCH_START = const(1)
TOUCH_MOVE = const(2)
TOUCH_END = const(4)
HID_READ = const(8)

time_queue = []
time_queue_ctr = 0
blocked_events = 0
blocked_gen = None


def schedule(gen, data=None, time=None):
    global time_queue_ctr
    if not time:
        time = utime.ticks_us()
    heappush(time_queue, (time, time_queue_ctr, gen, data))
    time_queue_ctr += 1


class Sleep():

    def __init__(self, us):
        self.time = utime.ticks_us() + us


class Select():

    def __init__(self, events):
        self.events = events


class Wait():

    def __init__(self, gens, wait_for=1, exit_others=True):
        self.wait_for = wait_for
        self.exit_others = exit_others
        self.received = 0
        self.callback = None
        self.gens = gens

        for g in gens:
            schedule(self._wait(g))

    def _wait(self, gen):
        if isinstance(gen, type_gen):
            ret = yield from gen
        else:
            ret = yield gen

        self.finish(gen, ret)

    def finish(self, gen, result):
        self.received += 1

        if self.received == self.wait_for:
            schedule(self.callback, (gen, result))
            self.callback = None

            if self.exit_others:
                for g in self.gens:
                    if isinstance(gen, type_gen):
                        g.close()


def run_forever():
    if __debug__:
        global log_delay_pos, log_delay_rb, log_delay_rb_len
    global blocked_events, blocked_gen

    DELAY_MAX = const(1000000)

    while True:

        # Peek at how long we can sleep while waiting for an event
        if time_queue:
            t, _, _, _ = time_queue[0]
            delay = t - utime.ticks_us()
        else:
            delay = DELAY_MAX

        if __debug__:
            # Adding current delay to ring buffer for performance stats
            log_delay_rb[log_delay_pos] = delay
            log_delay_pos = (log_delay_pos + 1) % log_delay_rb_len

        message = msg.select(delay)
        if message:
            # Run interrupt handler right away, they have priority
            event = message[0]
            data = message
            if blocked_events & event:
                gen = blocked_gen
                blocked_events = 0
                blocked_gen = None
            else:
                log.info(__name__, 'No handler for event: %s', event)
                continue
        else:
            # Run something from the time queue
            if time_queue:
                _, _, gen, data = heappop(time_queue)
            else:
                continue

        try:
            result = gen.send(data)
        except StopIteration as e:
            log.debug(__name__, '%s finished', gen)
            continue
        except Exception as e:
            log.exception(__name__, e)
            continue

        if isinstance(result, Sleep):
            # Sleep until result.time, call us later
            schedule(gen, None, result.time)

        elif isinstance(result, Select):
            # Wait for one or more types of event
            if blocked_gen:
                blocked_gen.close()
            blocked_gen = gen
            blocked_events = result.events

        elif isinstance(result, Wait):
            # Register the origin generator as a waiting callback
            result.callback = gen

        elif result is None:
            # Just call us asap
            schedule(gen)

        else:
            raise Exception('Unhandled result %s by %s' % (result, gen))
