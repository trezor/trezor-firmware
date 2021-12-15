"""
Implements an event loop with cooperative multitasking and async I/O.  Tasks in
the form of python coroutines (either plain generators or `async` functions) are
stepped through until completion, and can get asynchronously blocked by
`yield`ing or `await`ing a syscall.

See `schedule`, `run`, and syscalls `sleep`, `wait`, `signal` and `race`.
"""

import utime
import utimeq

from trezor import io, log

if False:
    from typing import (
        Any,
        Awaitable,
        Callable,
        Coroutine,
        Generator,
    )

    Task = Coroutine
    Finalizer = Callable[[Task, Any], None]

# function to call after every task step
after_step_hook: Callable[[], None] | None = None

# tasks scheduled for execution in the future
_queue = utimeq.utimeq(64)

# tasks paused on I/O
_paused: dict[int, set[Task]] = {}

# functions to execute after a task is finished
_finalizers: dict[int, Finalizer] = {}

# reference to the task that is currently executing
this_task: Task | None = None

if __debug__:
    # synthetic event queue
    synthetic_events: list[tuple[int, Any]] = []


class TaskClosed(Exception):
    pass


TASK_CLOSED = TaskClosed()


def schedule(
    task: Task,
    value: Any = None,
    deadline: int | None = None,
    finalizer: Finalizer | None = None,
    reschedule: bool = False,
) -> None:
    """
    Schedule task to be executed with `value` on given `deadline` (in
    microseconds).  Does not start the event loop itself, see `run`.
    Usually done in very low-level cases, see `race` for more user-friendly
    and correct concept.

    If `reschedule` is set, updates an existing entry.
    """
    if reschedule:
        _queue.discard(task)
    if deadline is None:
        deadline = utime.ticks_ms()
    if finalizer is not None:
        _finalizers[id(task)] = finalizer
    _queue.push(deadline, task, value)


def pause(task: Task, iface: int) -> None:
    """
    Block task on given message interface.  Task is resumed when the interface
    is activated.  It is most probably wrong to call `pause` from user code,
    see the `wait` syscall for the correct concept.
    """
    tasks = _paused.get(iface, None)
    if tasks is None:
        tasks = _paused[iface] = set()
    tasks.add(task)


def finalize(task: Task, value: Any) -> None:
    """Call and remove any finalization callbacks registered for given task."""
    fn = _finalizers.pop(id(task), None)
    if fn is not None:
        fn(task, value)


def close(task: Task) -> None:
    """
    Unschedule and unblock a task, close it so it can release all resources, and
    call its finalizer.
    """
    for iface in _paused:  # pylint: disable=consider-using-dict-items
        _paused[iface].discard(task)
    _queue.discard(task)
    task.close()
    finalize(task, GeneratorExit())


def run() -> None:
    """
    Loop forever, stepping through scheduled tasks and awaiting I/O events
    in between.  Use `schedule` first to add a coroutine to the task queue.
    Tasks yield back to the scheduler on any I/O, usually by calling `await` on
    a `Syscall`.
    """
    task_entry = [0, 0, 0]  # deadline, task, value
    msg_entry = [0, 0]  # iface | flags, value
    while _queue or _paused:
        if __debug__:
            # process synthetic events
            if synthetic_events:
                iface, event = synthetic_events[0]
                msg_tasks = _paused.pop(iface, ())
                if msg_tasks:
                    synthetic_events.pop(0)
                    for task in msg_tasks:
                        _step(task, event)

                    # XXX: we assume that synthetic events are rare. If there is a lot of them,
                    # this degrades to "while synthetic_events" and would ignore all real ones.
                    continue

        # compute the maximum amount of time we can wait for a message
        if _queue:
            delay = utime.ticks_diff(_queue.peektime(), utime.ticks_ms())
        else:
            delay = 1000  # wait for 1 sec maximum if queue is empty

        if io.poll(_paused, msg_entry, delay):
            # message received, run tasks paused on the interface
            msg_tasks = _paused.pop(msg_entry[0], ())
            for task in msg_tasks:
                _step(task, msg_entry[1])
        else:
            # timeout occurred, run the first scheduled task
            if _queue:
                _queue.pop(task_entry)
                _step(task_entry[1], task_entry[2])  # type: ignore
                # error: Argument 1 to "_step" has incompatible type "int"; expected "Coroutine[Any, Any, Any]"
                # rationale: We use untyped lists here, because that is what the C API supports.


def clear() -> None:
    """Clear all queue state.  Any scheduled or paused tasks will be forgotten."""
    _ = [0, 0, 0]
    while _queue:
        _queue.pop(_)
    _paused.clear()
    _finalizers.clear()


def _step(task: Task, value: Any) -> None:
    """
    Step through the task by sending value to it. This can result in either:
    1. The task raises an exception:
        a) StopIteration
            - The Task is completed and we call finalize() to finish it.
        b) Exception
            - An error occurred. We still need to call finalize().
    2. Task does not raise exception and returns either:
        a) Syscall
            - Syscall.handle() is called.
        b) None
            - The Task is simply scheduled to continue.
        c) Something else
            - This should not happen - error.
    """
    global this_task
    this_task = task
    try:
        if isinstance(value, BaseException):
            result = task.throw(value)
        else:
            result = task.send(value)
    except StopIteration as e:
        if __debug__:
            log.debug(__name__, "finish: %s", task)
        finalize(task, e.value)
    except Exception as e:
        if __debug__:
            log.exception(__name__, e)
        finalize(task, e)
    else:
        if isinstance(result, Syscall):
            result.handle(task)
        elif result is None:
            schedule(task)
        else:
            if __debug__:
                log.error(__name__, "unknown syscall: %s", result)
        if after_step_hook:
            after_step_hook()


class Syscall:
    """
    When tasks want to perform any I/O, or do any sort of communication with the
    scheduler, they do so through instances of a class derived from `Syscall`.
    """

    def __iter__(self) -> Task:  # type: ignore
        # support `yield from` or `await` on syscalls
        return (yield self)

    def __await__(self) -> Generator:
        return self.__iter__()  # type: ignore

    def handle(self, task: Task) -> None:
        pass


SLEEP_FOREVER = Syscall()
"""Tasks awaiting `SLEEP_FOREVER` will never be resumed."""


class sleep(Syscall):
    """Pause current task and resume it after given delay.

    Result value is the calculated deadline.

    Example:

    >>> planned = await loop.sleep(1000)  # sleep for 1s
    >>> print(f"missed by {utime.ticks_diff(utime.ticks_ms(), planned)} ms")
    """

    def __init__(self, delay_ms: int) -> None:
        self.delay_ms = delay_ms

    def handle(self, task: Task) -> None:
        deadline = utime.ticks_add(utime.ticks_ms(), self.delay_ms)
        schedule(task, deadline, deadline)


class wait(Syscall):
    """
    Pause current task, and resume only after a message on `msg_iface` is
    received.  Messages are received either from an USB interface, or the
    touch display.  Result value is a tuple of message values.

    Example:

    >>> hid_report, = await loop.wait(0xABCD)  # await USB HID report
    >>> event, x, y = await loop.wait(io.TOUCH)  # await touch event
    """

    def __init__(self, msg_iface: int) -> None:
        self.msg_iface = msg_iface

    def handle(self, task: Task) -> None:
        pause(task, self.msg_iface)


_type_gen = type((lambda: (yield))())


class race(Syscall):
    """
    Given a list of either children tasks or syscalls, `race` waits until one of
    them completes (tasks are executed in parallel, syscalls are waited upon,
    directly).  Return value of `race` is the return value of the child that
    triggered the  completion.  Other running children are killed (by cancelling
    any pending schedules and raising a `GeneratorExit` by calling `close()`).
    Child that caused the completion is present in `self.finished`.

    Example:

    >>> # async def wait_for_touch(): ...
    >>> # async def animate_logo(): ...
    >>> touch_task = wait_for_touch()
    >>> animation_task = animate_logo()
    >>> racer = loop.race(touch_task, animation_task)
    >>> result = await racer
    >>> if animation_task in racer.finished:
    >>>     print('animation task returned value:', result)
    >>> elif touch_task in racer.finished:
    >>>     print('touch task returned value:', result)

    Note: You should not directly `yield` a `race` instance, see logic in
    `race.__iter__` for explanation.  Always use `await`.
    """

    def __init__(self, *children: Awaitable, exit_others: bool = True) -> None:
        self.children = children
        self.exit_others = exit_others
        self.finished: list[Awaitable] = []  # children that finished
        self.scheduled: list[Task] = []  # scheduled wrapper tasks

    def handle(self, task: Task) -> None:
        """
        Schedule all children Tasks and set `task` as callback.
        """
        finalizer = self._finish
        scheduled = self.scheduled
        finished = self.finished

        self.callback = task
        scheduled.clear()
        finished.clear()

        for child in self.children:
            if isinstance(child, _type_gen):
                child_task = child
            else:
                child_task = iter(child)  # type: ignore
            schedule(child_task, None, None, finalizer)
            scheduled.append(child_task)
            # TODO: document the types here

    def exit(self, except_for: Task | None = None) -> None:
        for task in self.scheduled:
            if task != except_for:
                close(task)

    def _finish(self, task: Task, result: Any) -> None:
        if not self.finished:
            # because we create tasks for children that are not generators yet,
            # we need to find the child value that the caller supplied
            for index, child_task in enumerate(self.scheduled):
                if child_task is task:
                    child = self.children[index]
                    break
            self.finished.append(child)
            if self.exit_others:
                self.exit(task)
            schedule(self.callback, result)

    def __iter__(self) -> Task:  # type: ignore
        try:
            return (yield self)
        except:  # noqa: E722
            # exception was raised on the waiting task externally with
            # close() or throw(), kill the children tasks and re-raise
            # Make sure finalizers don't continue processing.
            self.finished.append(self)
            self.exit()
            raise


class chan:
    """
    Two-ended channel.
    The receiving end pauses until a value to be received is available. The sending end
    can choose to wait until the value is received, or it can publish the value without
    waiting.

    Example:

    >>> # in task #1:
    >>> signal = loop.chan()
    >>> while True:
    >>>     result = await signal.take()
    >>>     print("awaited result:", result)

    >>> # in task #2:
    >>> signal.publish("Published without waiting")
    >>> print("publish completed")
    >>> await signal.put("Put with await")
    >>> print("put completed")

    Example Output:

    publish completed
    awaited result: Published without waiting
    awaited result: Put with await
    put completed
    """

    class Put(Syscall):
        def __init__(self, ch: "chan", value: Any) -> None:
            self.ch = ch
            self.value = value
            self.task: Task | None = None

        def handle(self, task: Task) -> None:
            self.task = task
            self.ch._schedule_put(task, self.value)

    class Take(Syscall):
        def __init__(self, ch: "chan") -> None:
            self.ch = ch
            self.task: Task | None = None

        def handle(self, task: Task) -> None:
            self.task = task
            self.ch._schedule_take(task)

    def __init__(self) -> None:
        self.putters: list[tuple[Task | None, Any]] = []
        self.takers: list[Task] = []

    def put(self, value: Any) -> Awaitable[None]:  # type: ignore
        put = chan.Put(self, value)
        try:
            return (yield put)
        except:  # noqa: E722
            entry = (put.task, value)
            if entry in self.putters:
                self.putters.remove(entry)
            raise

    def take(self) -> Awaitable[Any]:  # type: ignore
        take = chan.Take(self)
        try:
            return (yield take)
        except:  # noqa: E722
            if take.task in self.takers:
                self.takers.remove(take.task)
            raise

    def publish(self, value: Any) -> None:
        if self.takers:
            taker = self.takers.pop(0)
            schedule(taker, value)
        else:
            self.putters.append((None, value))

    def _schedule_put(self, putter: Task, value: Any) -> bool:
        if self.takers:
            taker = self.takers.pop(0)
            schedule(taker, value)
            schedule(putter)
            return True
        else:
            self.putters.append((putter, value))
            return False

    def _schedule_take(self, taker: Task) -> None:
        if self.putters:
            putter, value = self.putters.pop(0)
            schedule(taker, value)
            if putter is not None:
                schedule(putter)
        else:
            self.takers.append(taker)


class spawn(Syscall):
    """Spawn a task asynchronously and get an awaitable reference to it.

    Abstraction over `loop.schedule` and `loop.close`. Useful when you need to start
    a task in the background, but want to be able to kill it from the outside.

    Examples:

    1. Spawn a background task, get its result later.

    >>> wire_read = loop.spawn(read_from_wire())
    >>> long_result = await long_running_operation()
    >>> wire_result = await wire_read

    2. Allow the user to kill a long-running operation:

    >>> try:
    >>>     operation = loop.spawn(long_running_operation())
    >>>     result = await operation
    >>>     print("finished with result", result)
    >>> except loop.TaskClosed:
    >>>     print("task was closed before it could finish")
    >>>
    >>> # meanwhile, on the other side of town...
    >>> controller.close()

    Task is spawned only once. Multiple attempts to `await spawned_object` will return
    the original return value (or raise the original exception).
    """

    def __init__(self, task: Task) -> None:
        self.task = task
        self.callback: Task | None = None
        self.finalizer_callback: Callable[["spawn"], None] | None = None
        self.finished = False
        self.return_value: Any = None

        # schedule task immediately
        if __debug__:
            log.debug(__name__, "spawn new task: %s", task)
        schedule(task, finalizer=self._finalize)

    def _finalize(self, task: Task, value: Any) -> None:
        # sanity check: make sure finalizer is for our task
        assert task is self.task
        # sanity check: make sure finalizer is not called more than once
        assert self.finished is False

        # now we are truly finished
        self.finished = True
        if isinstance(value, GeneratorExit):
            # coerce GeneratorExit to a catchable TaskClosed
            self.return_value = TASK_CLOSED
        else:
            self.return_value = value

        if self.callback is not None:
            schedule(self.callback, self.return_value)
            self.callback = None
        if self.finalizer_callback is not None:
            self.finalizer_callback(self)

    def __iter__(self) -> Task:  # type: ignore
        if self.finished:
            # exit immediately if we already have a return value
            if isinstance(self.return_value, BaseException):
                raise self.return_value
            else:
                return self.return_value

        try:
            return (yield self)
        except BaseException:
            # Clear out the callback. Otherwise we would raise the exception into it,
            # AND schedule it with the closing value of the child task.
            self.callback = None
            assert self.task is not this_task  # closing parent from child :(
            close(self.task)
            raise

    def handle(self, caller: Task) -> None:
        # the same spawn should not be awaited multiple times
        assert self.callback is None
        self.callback = caller

    def close(self) -> None:
        """Shut down the spawned task.

        If another caller is awaiting its result it will get a TaskClosed exception.
        If the task was already finished, the call has no effect.
        """
        if not self.finished:
            if __debug__:
                log.debug(__name__, "close spawned task: %s", self.task)
            close(self.task)

    def set_finalizer(self, finalizer_callback: Callable[["spawn"], None]) -> None:
        """Register a finalizer callback.

        The provided function is executed synchronously when the spawned task ends,
        with the spawn object as an argument.
        """
        if self.finished:
            finalizer_callback(self)
        self.finalizer_callback = finalizer_callback

    def is_running(self) -> bool:
        """Check if the caller is executing from the spawned task.

        Useful for checking if it is OK to call `task.close()`. If `task.is_running()`
        is True, it would be calling close on self, which will result in a ValueError.
        """
        return self.task is this_task
