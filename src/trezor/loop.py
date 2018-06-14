'''
Implements an event loop with cooperative multitasking and async I/O.  Tasks in
the form of python coroutines (either plain generators or `async` functions) are
stepped through until completion, and can get asynchronously blocked by
`yield`ing or `await`ing a syscall.

See `schedule`, `run`, and syscalls `sleep`, `wait`, `signal` and `spawn`.
'''

import utime
import utimeq
from micropython import const
from trezor import log
from trezor import io

after_step_hook = None  # function, called after each task step

_QUEUE_SIZE = const(64)  # maximum number of scheduled tasks
_queue = utimeq.utimeq(_QUEUE_SIZE)
_paused = {}

if __debug__:
    # for performance stats
    import array
    log_delay_pos = 0
    log_delay_rb_len = const(10)
    log_delay_rb = array.array('i', [0] * log_delay_rb_len)


def schedule(task, value=None, deadline=None):
    '''
    Schedule task to be executed with `value` on given `deadline` (in
    microseconds).  Does not start the event loop itself, see `run`.
    '''
    if deadline is None:
        deadline = utime.ticks_us()
    _queue.push(deadline, task, value)


def pause(task, iface):
    tasks = _paused.get(iface, None)
    if tasks is None:
        tasks = _paused[iface] = set()
    tasks.add(task)


def close(task):
    for iface in _paused:
        _paused[iface].discard(task)
    _queue.discard(task)
    task.close()


def run():
    '''
    Loop forever, stepping through scheduled tasks and awaiting I/O events
    inbetween.  Use `schedule` first to add a coroutine to the task queue.
    Tasks yield back to the scheduler on any I/O, usually by calling `await` on
    a `Syscall`.
    '''

    if __debug__:
        global log_delay_pos

    max_delay = const(1000000)  # usec delay if queue is empty

    task_entry = [0, 0, 0]  # deadline, task, value
    msg_entry = [0, 0]  # iface | flags, value
    while _queue or _paused:
        # compute the maximum amount of time we can wait for a message
        if _queue:
            delay = utime.ticks_diff(_queue.peektime(), utime.ticks_us())
        else:
            delay = max_delay

        if __debug__:
            # add current delay to ring buffer for performance stats
            log_delay_rb[log_delay_pos] = delay
            log_delay_pos = (log_delay_pos + 1) % log_delay_rb_len

        if io.poll(_paused, msg_entry, delay):
            # message received, run tasks paused on the interface
            msg_tasks = _paused.pop(msg_entry[0], ())
            for task in msg_tasks:
                _step(task, msg_entry[1])
        else:
            # timeout occurred, run the first scheduled task
            if _queue:
                _queue.pop(task_entry)
                _step(task_entry[1], task_entry[2])


def _step(task, value):
    try:
        if isinstance(value, Exception):
            result = task.throw(value)
        else:
            result = task.send(value)
    except StopIteration as e:
        if __debug__:
            log.debug(__name__, 'finish: %s', task)
    except Exception as e:
        if __debug__:
            log.exception(__name__, e)
    else:
        if isinstance(result, Syscall):
            result.handle(task)
        elif result is None:
            schedule(task)
        else:
            if __debug__:
                log.error(__name__, 'unknown syscall: %s', result)
        if after_step_hook:
            after_step_hook()


class Syscall:
    '''
    When tasks want to perform any I/O, or do any sort of communication with the
    scheduler, they do so through instances of a class derived from `Syscall`.
    '''

    def __iter__(self):
        # support `yield from` or `await` on syscalls
        return (yield self)


class sleep(Syscall):
    '''
    Pause current task and resume it after given delay.  Although the delay is
    given in microseconds, sub-millisecond precision is not guaranteed.  Result
    value is the calculated deadline.

    Example:

    >>> planned = await loop.sleep(1000 * 1000)  # sleep for 1ms
    >>> print('missed by %d us', utime.ticks_diff(utime.ticks_us(), planned))
    '''

    def __init__(self, delay_us):
        self.delay_us = delay_us

    def handle(self, task):
        deadline = utime.ticks_add(utime.ticks_us(), self.delay_us)
        schedule(task, deadline, deadline)


class wait(Syscall):
    '''
    Pause current task, and resume only after a message on `msg_iface` is
    received.  Messages are received either from an USB interface, or the
    touch display.  Result value a tuple of message values.

    Example:

    >>> hid_report, = await loop.wait(0xABCD)  # await USB HID report
    >>> event, x, y = await loop.wait(io.TOUCH)  # await touch event
    '''

    def __init__(self, msg_iface):
        self.msg_iface = msg_iface

    def handle(self, task):
        pause(task, self.msg_iface)


_NO_VALUE = ()


class signal(Syscall):
    '''
    Pause current task, and let other running task to resume it later with a
    result value or an exception.

    Example:

    >>> # in task #1:
    >>> signal = loop.signal()
    >>> result = await signal
    >>> print('awaited result:', result)
    >>> # in task #2:
    >>> signal.send('hello from task #2')
    >>> # prints in the next iteration of the event loop
    '''

    def __init__(self):
        self.value = _NO_VALUE
        self.task = None

    def handle(self, task):
        self.task = task
        self._deliver()

    def send(self, value):
        self.value = value
        self._deliver()

    def _deliver(self):
        if self.task is not None and self.value is not _NO_VALUE:
            schedule(self.task, self.value)
            self.task = None
            self.value = _NO_VALUE

    def __iter__(self):
        try:
            return (yield self)
        except:  # noqa: E722
            self.task = None
            raise


class spawn(Syscall):
    '''
    Execute one or more children tasks and wait until one of them exits.
    Return value of `spawn` is the return value of task that triggered the
    completion.  By default, `spawn` returns after the first child completes, and
    other running children are killed (by cancelling any pending schedules and
    calling `close()`).

    Example:

    >>> # async def wait_for_touch(): ...
    >>> # async def animate_logo(): ...
    >>> touch_task = wait_for_touch()
    >>> animation_task = animate_logo()
    >>> waiter = loop.spawn(touch_task, animation_task)
    >>> result = await waiter
    >>> if animation_task in waiter.finished:
    >>>     print('animation task returned', result)
    >>> else:
    >>>     print('touch task returned', result)

    Note: You should not directly `yield` a `spawn` instance, see logic in
    `spawn.__iter__` for explanation.  Always use `await`.
    '''

    def __init__(self, *children, exit_others=True):
        self.children = children
        self.exit_others = exit_others
        self.scheduled = None  # list of scheduled wrapper tasks
        self.finished = None  # list of children that finished
        self.callback = None

    def handle(self, task):
        self.callback = task
        self.finished = []
        self.scheduled = []
        for index, child in enumerate(self.children):
            parent = self._wait(child, index)
            schedule(parent)
            self.scheduled.append(parent)

    def exit(self, skip_index=-1):
        for index, parent in enumerate(self.scheduled):
            if index != skip_index:
                close(parent)

    async def _wait(self, child, index):
        try:
            result = await child
        except Exception as e:
            self._finish(child, index, e)
        else:
            self._finish(child, index, result)

    def _finish(self, child, index, result):
        if not self.finished:
            self.finished.append(child)
            if self.exit_others:
                self.exit(index)
            schedule(self.callback, result)

    def __iter__(self):
        try:
            return (yield self)
        except:  # noqa: E722
            # exception was raised on the waiting task externally with
            # close() or throw(), kill the children tasks and re-raise
            self.exit()
            raise


class put(Syscall):

    def __init__(self, ch, value=None):
        self.ch = ch
        self.value = value

    def __call__(self, value):
        self.value = value
        return self

    def handle(self, task):
        self.ch.schedule_put(schedule, task, self.value)


class take(Syscall):

    def __init__(self, ch):
        self.ch = ch

    def __call__(self):
        return self

    def handle(self, task):
        if self.ch.schedule_take(schedule, task) and self.ch.id is not None:
            pause(self.ch, self.ch.id)


class chan:

    def __init__(self, id=None):
        self.id = id
        self.putters = []
        self.takers = []
        self.put = put(self)
        self.take = take(self)

    def schedule_publish(self, schedule, value):
        if self.takers:
            for taker in self.takers:
                schedule(taker, value)
            self.takers.clear()
            return True
        else:
            return False

    def schedule_put(self, schedule, putter, value):
        if self.takers:
            taker = self.takers.pop(0)
            schedule(taker, value)
            schedule(putter, value)
            return True
        else:
            self.putters.append((putter, value))
            return False

    def schedule_take(self, schedule, taker):
        if self.putters:
            putter, value = self.putters.pop(0)
            schedule(taker, value)
            schedule(putter, value)
            return True
        else:
            self.takers.append(taker)
            return False
