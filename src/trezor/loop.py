import utime

from uheapq import heappop, heappush, heapify
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

blocked_gens = {}  # event -> generator
time_queue = []  # [(int, int, generator, any)]
time_ticket = 0


def schedule(gen, data=None, time=None):
    global time_ticket
    if not time:
        time = utime.ticks_us()
    heappush(time_queue, (time, time_ticket, gen, data))
    time_ticket += 1
    return gen


def unschedule(gen):
    global time_queue
    time_queue = [entry for entry in time_queue if entry[1] is not gen]
    heapify(time_queue)


def block(gen, event):
    curr_gen = blocked_gens.get(event, None)
    if curr_gen is not None:
        log.warning(__name__, 'Closing %s blocked on %s', curr_gen, event)
        curr_gen.close()
    blocked_gens[event] = gen


def unblock(gen):
    for key in blocked_gens:
        if blocked_gens[key] is gen:
            blocked_gens[key] = None


class Sleep():

    def __init__(self, us):
        self.time = utime.ticks_us() + us


class Select():

    def __init__(self, *events):
        self.events = events

    def handle(self, gen):
        for event in self.events:
            block(gen, event)


class Wait():

    def __init__(self, gens, wait_for=1, exit_others=True):
        self.gens = gens
        self.wait_for = wait_for
        self.exit_others = exit_others
        self.scheduled = []
        self.finished = []
        self.callback = None

    def handle(self, gen):
        self.scheduled = [schedule(self._wait(gen)) for gen in self.gens]
        self.callback = gen

    def exit(self):
        for gen in self.scheduled:
            if gen not in self.finished and isinstance(gen, type_gen):
                unschedule(gen)
                unblock(gen)
                gen.close()

    def _wait(self, gen):
        try:
            if isinstance(gen, type_gen):
                result = yield from gen
            else:
                result = yield gen
        except Exception as exc:
            self._finish(gen, exc)
        else:
            self._finish(gen, result)

    def _finish(self, gen, result):
        self.finished.append(gen)
        if self.wait_for == len(self.finished) or isinstance(result, Exception):
            if self.exit_others:
                self.exit()
            schedule(self.callback, result)
            self.callback = None


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
            gen = blocked_gens.pop(event, None)
            if not gen:
                log.info(__name__, 'No handler for event: %s', event)
                continue
            # Cancel other registrations of this handler
            unblock(gen)
        else:
            # Run something from the time queue
            if time_queue:
                _, _, gen, data = heappop(time_queue)
            else:
                continue

        try:
            if isinstance(data, Exception):
                result = gen.throw(data)
            else:
                result = gen.send(data)
        except StopIteration as e:
            log.debug(__name__, '%s finished', gen)
            continue
        except Exception as e:
            log.exception(__name__, e)
            continue

        if isinstance(result, Sleep):
            # Sleep until result.time, call us later
            schedule(gen, result, result.time)

        elif isinstance(result, Select):
            # Wait for one or more types of event
            result.handle(gen)

        elif isinstance(result, Wait):
            # Register us as a waiting callback
            result.handle(gen)

        elif result is None:
            # Just call us asap
            schedule(gen)

        else:
            raise Exception('Unhandled result %s by %s' % (result, gen))
