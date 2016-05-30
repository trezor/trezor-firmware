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

# Touch interface
TOUCH = const(256)  # 0-255 is reserved for USB interfaces
TOUCH_START = const(1)
TOUCH_MOVE = const(2)
TOUCH_END = const(3)

msg_handlers = {}  # Interface -> generator
time_queue = []
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


def block(gen, iface):
    curr = msg_handlers.get(iface, None)
    if curr:
        log.warning(__name__, 'Closing %s blocked on %s', curr, iface)
        curr.close()
    msg_handlers[iface] = gen


def unblock(gen):
    for iface in msg_handlers:
        if msg_handlers[iface] is gen:
            msg_handlers[iface] = None


class Syscall():
    pass


class Sleep(Syscall):

    def __init__(self, us):
        self.time = utime.ticks_us() + us

    def register(self, gen):
        schedule(gen, self, self.time)


class Select(Syscall):

    def __init__(self, iface):
        self.iface = iface

    def register(self, gen):
        block(gen, self.iface)


class Wait(Syscall):

    def __init__(self, gens, wait_for=1, exit_others=True):
        self.gens = gens
        self.wait_for = wait_for
        self.exit_others = exit_others
        self.scheduled = []
        self.finished = []
        self.callback = None

    def register(self, gen):
        self.scheduled = [schedule(self._wait(g)) for g in self.gens]
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
            iface = message[0]
            data = message
            gen = msg_handlers.pop(iface, None)
            if not gen:
                log.info(__name__, 'No handler for message: %s', iface)
                continue
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

        if isinstance(result, Syscall):
            # Execute the syscall
            result.register(gen)

        elif result is None:
            # Just call us asap
            schedule(gen)

        else:
            raise Exception('Unhandled result %s by %s' % (result, gen))
