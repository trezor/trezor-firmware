'''
Implements an event loop with cooperative multitasking and async I/O.  Tasks in
the form of python coroutines (either plain generators or `async` functions) are
stepped through until completion, and can get asynchronously blocked by
`yield`ing or `await`ing a syscall.

See `schedule_task`, `run_forever`, and syscalls `Sleep`, `Select`, `Signal`
and `Wait`.
'''

import utime
import utimeq
from micropython import const
from trezor import msg
from trezor import log

TOUCH = const(255)  # interface
TOUCH_START = const(1)  # event
TOUCH_MOVE = const(2)  # event
TOUCH_END = const(4)  # event

after_step_hook = None  # function, called after each task step

_MAX_SELECT_DELAY = const(1000000)  # usec delay if queue is empty
_MAX_QUEUE_SIZE = const(64)  # maximum number of scheduled tasks

_paused_tasks = {}  # {message interface: [task]}
_scheduled_tasks = utimeq.utimeq(_MAX_QUEUE_SIZE)

if __debug__:
    # for performance stats
    import array
    log_delay_pos = 0
    log_delay_rb_len = const(10)
    log_delay_rb = array.array('i', [0] * log_delay_rb_len)


def schedule_task(task, value=None, deadline=None):
    '''
    Schedule task to be executed with `value` on given `deadline` (in
    microseconds).  Does not start the event loop itself, see `run_forever`.
    '''
    if deadline is None:
        deadline = utime.ticks_us()
    _scheduled_tasks.push(deadline, task, value)


def unschedule_task(task):
    '''
    Remove task from the time queue.  Cancels previous `schedule_task`.
    '''
    global _scheduled_tasks
    task_entry = [0, 0, 0]  # deadline, task, value
    queue_copy = utimeq.utimeq(_MAX_QUEUE_SIZE)
    while _scheduled_tasks:
        _scheduled_tasks.pop(task_entry)
        if task_entry[1] is not task:
            queue_copy.push(task_entry[0], task_entry[1], task_entry[2])
    _scheduled_tasks = queue_copy


def _pause_task(task, iface):
    tasks = _paused_tasks.get(iface, None)
    if tasks is None:
        tasks = _paused_tasks[iface] = []
    tasks.append(task)


def _unpause_task(task):
    for iface in _paused_tasks:
        if task in _paused_tasks[iface]:
            _paused_tasks[iface].remove(task)


def run_forever():
    '''
    Loop forever, stepping through scheduled tasks and awaiting I/O events
    inbetween.  Use `schedule_task` first to add a coroutine to the task queue.
    Tasks yield back to the scheduler on any I/O, usually by calling `await` on
    a `Syscall`.
    '''

    if __debug__:
        global log_delay_pos

    task_entry = [0, 0, 0]  # deadline, task, value
    while True:
        # compute the maximum amount of time we can wait for a message
        if _scheduled_tasks:
            delay = utime.ticks_diff(
                _scheduled_tasks.peektime(), utime.ticks_us())
        else:
            delay = _MAX_SELECT_DELAY

        if __debug__:
            # add current delay to ring buffer for performance stats
            log_delay_rb[log_delay_pos] = delay
            log_delay_pos = (log_delay_pos + 1) % log_delay_rb_len

        msg_entry = msg.select(delay)
        if msg_entry is not None:
            # message received, run tasks paused on the interface
            msg_iface, *msg_value = msg_entry
            msg_tasks = _paused_tasks.pop(msg_iface, ())
            for task in msg_tasks:
                _step_task(task, msg_value)
        else:
            # timeout occurred, run the first scheduled task
            if _scheduled_tasks:
                _scheduled_tasks.pop(task_entry)
                _step_task(task_entry[1], task_entry[2])


def _step_task(task, value):
    try:
        if isinstance(value, Exception):
            result = task.throw(value)
        else:
            result = task.send(value)
    except StopIteration as e:
        log.debug(__name__, '%s finished', task)
    except Exception as e:
        log.exception(__name__, e)
    else:
        if isinstance(result, Syscall):
            result.handle(task)
        elif result is None:
            schedule_task(task)
        else:
            log.error(__name__, '%s is unknown syscall', result)
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


class Sleep(Syscall):
    '''
    Pause current task and resume it after given delay.  Although the delay is
    given in microseconds, sub-millisecond precision is not guaranteed.  Result
    value is the calculated deadline.

    Example:
        planned = await loop.Sleep(1000 * 1000)  # sleep for 1ms
        print('missed by %d us', utime.ticks_diff(utime.ticks_us(), planned))
    '''

    def __init__(self, delay_us):
        self.delay_us = delay_us

    def handle(self, task):
        deadline = utime.ticks_add(utime.ticks_us(), self.delay_us)
        schedule_task(task, deadline, deadline)


class Select(Syscall):
    '''
    Pause current task, and resume only after a message on `msg_iface` is
    received.  Messages are received either from an USB interface, or the
    touch display.  Result value a tuple of message values.

    Example:
        hid_report, = await loop.Select(0xABCD)  # await USB HID report
        event, x, y = await loop.Select(loop.TOUCH)  # await touch event
    '''

    def __init__(self, msg_iface):
        self.msg_iface = msg_iface

    def handle(self, task):
        _pause_task(task, self.msg_iface)


_NO_VALUE = ()


class Signal(Syscall):
    '''
    Pause current task, and let other running task to resume it later with a
    result value or an exception.

    Example:
        # in task #1:
        signal = loop.Signal()
        result = await signal
        print('awaited result:', result)
        # in task #2:
        signal.send('hello from task #2')
        # prints in the next iteration of the event loop
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
            schedule_task(self.task, self.value)
            self.task = None
            self.value = _NO_VALUE


class Wait(Syscall):
    '''
    Execute one or more children tasks and wait until one or more of them exit.
    Return value of `Wait` is the return value of task that triggered the
    completion.  By default, `Wait` returns after the first child completes, and
    other running children are killed (by cancelling any pending schedules and
    calling `close()`).

    Example:
        # async def wait_for_touch(): ...
        # async def animate_logo(): ...
        touch_task = wait_for_touch()
        animation_task = animate_logo()
        waiter = loop.Wait((touch_task, animation_task))
        result = await waiter
        if animation_task in waiter.finished:
            print('animation task returned', result)
        else:
            print('touch task returned', result)

    Note: You should not directly `yield` a `Wait` instance, see logic in
    `Wait.__iter__` for explanation.  Always use `await`.
    '''

    def __init__(self, children, wait_for=1, exit_others=True):
        self.children = children
        self.wait_for = wait_for
        self.exit_others = exit_others
        self.scheduled = None
        self.finished = None
        self.callback = None

    def handle(self, task):
        self.callback = task
        self.finished = []
        self.scheduled = [self._wait(c) for c in self.children]
        for ct in self.scheduled:
            schedule_task(ct)

    def exit(self):
        for task in self.scheduled:
            if task not in self.finished:
                _unpause_task(task)
                unschedule_task(task)
                task.close()

    async def _wait(self, child):
        try:
            result = await child
        except Exception as e:
            self._finish(child, e)
        else:
            self._finish(child, result)

    def _finish(self, child, result):
        self.finished.append(child)
        if self.wait_for == len(self.finished) or isinstance(result, Exception):
            if self.exit_others:
                self.exit()
            schedule_task(self.callback, result)

    def __iter__(self):
        try:
            return (yield self)
        except:
            # exception was raised on the waiting task externally with
            # close() or throw(), kill the children tasks and re-raise
            self.exit()
            raise

select = Select
sleep = Sleep
wait = Wait
signal = Signal
