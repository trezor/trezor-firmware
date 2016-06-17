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
TOUCH_END = const(4)

msg_handlers = {}  # Message interface -> [generator]
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
    if iface in msg_handlers:
        msg_handlers[iface].append(gen)
    else:
        msg_handlers[iface] = [gen]


def unblock(gen):
    for iface in msg_handlers:
        if gen in msg_handlers[iface]:
            msg_handlers[iface].remove(gen)


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
        self.scheduled = []  # In uPython, set() cannot contain generators
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


def step_task(gen, data):
    if isinstance(data, Exception):
        result = gen.throw(data)
    else:
        result = gen.send(data)
    if isinstance(result, Syscall):
        result.register(gen)  # Execute the syscall
    elif result is None:
        schedule(gen)  # Just call us asap
    else:
        raise Exception('Unhandled result %s by %s' % (result, gen))


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

        m = msg.select(delay)
        if m:
            # Run interrupt handlers right away, they have priority
            iface, *data = m
            tasks = msg_handlers.pop(iface, None)
            if not tasks:
                log.info(__name__, 'No handler for message: %s', iface)
                continue
        else:
            # Run something from the time queue
            if time_queue:
                _, _, gen, data = heappop(time_queue)
                tasks = (gen,)
            else:
                continue

        # Run the tasks
        for gen in tasks:
            try:
                step_task(gen, data)
            except StopIteration as e:
                log.debug(__name__, '%s finished', gen)
            except Exception as e:
                log.exception(__name__, e)
