"""
Implements an event loop with cooperative multitasking and async I/O.  Tasks in
the form of python coroutines (either plain generators or `async` functions) are
stepped through until completion, and can get asynchronously blocked by
`yield`ing or `await`ing a syscall.

See `schedule`, `run`, and syscalls `sleep`, `wait`, `signal` and `race`.
"""

import utime
import utimeq
from typing import TYPE_CHECKING

from trezor import io, log

if TYPE_CHECKING:
    from typing import Any, Awaitable, Callable, Coroutine, Generator, Union

    Task = Union[Coroutine, Generator, "wait"]
    AwaitableTask = Task | Awaitable
    Finalizer = Callable[[Task, Any], None]

# tasks scheduled for execution in the future
_queue = utimeq.utimeq(64)

# tasks paused on I/O
_paused: dict[int, set[Task]] = {}

# functions to execute after a task is finished
_finalizers: dict[int, Finalizer] = {}

# reference to the task that is currently executing
this_task: Task | None = None


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
    milliseconds).  Does not start the event loop itself, see `run`.
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
    for iface in _paused:  # pylint: disable=consider-using-dict-items
        if not _paused[iface]:
            del _paused[iface]
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
                _step(task_entry[1], task_entry[2])  # type: ignore [Argument of type "int" cannot be assigned to parameter "task" of type "Task" in function "_step"]
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


class Syscall:
    """
    When tasks want to perform any I/O, or do any sort of communication with the
    scheduler, they do so through instances of a class derived from `Syscall`.
    """

    def __iter__(self) -> Generator:
        # support `yield from` or `await` on syscalls
        return (yield self)

    if TYPE_CHECKING:

        def __await__(self) -> Generator[Any, Any, Any]:
            return self.__iter__()

    def handle(self, task: Task) -> None:
        pass


class Timeout(Exception):
    pass


_TIMEOUT_ERROR = Timeout()


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

    _DO_NOT_RESCHEDULE = Syscall()

    def __init__(self, msg_iface: int, timeout_ms: int | None = None) -> None:
        self.msg_iface = msg_iface
        self.timeout_ms = timeout_ms
        self.task: Task | None = None

    def handle(self, task: Task) -> None:
        self.task = task
        pause(self, self.msg_iface)
        if self.timeout_ms is not None:
            deadline = utime.ticks_add(utime.ticks_ms(), self.timeout_ms)
            schedule(self, _TIMEOUT_ERROR, deadline)

    def send(self, __value: Any) -> Any:
        assert self.task is not None
        self.close()
        _step(self.task, __value)
        return self._DO_NOT_RESCHEDULE

    throw = send

    def close(self) -> None:
        _queue.discard(self)
        if self.msg_iface in _paused:
            _paused[self.msg_iface].discard(self)
            if not _paused[self.msg_iface]:
                del _paused[self.msg_iface]

    def __iter__(self) -> Generator:
        try:
            return (yield self)
        finally:
            # whichever way we got here, we must be removed from the paused list
            self.close()


_type_gen: type[Generator] = type((lambda: (yield))())


class race(Syscall):
    """
    Given a list of either children tasks or syscalls, `race` waits until one of
    them completes (tasks are executed in parallel, syscalls are waited upon,
    directly).  Return value of `race` is the return value of the child that
    triggered the  completion.  Other running children are killed (by cancelling
    any pending schedules and raising a `GeneratorExit` by calling `close()`).

    Example:

    >>> # async def wait_for_touch(): ...
    >>> # async def animate_logo(): ...
    >>> touch_task = wait_for_touch()
    >>> animation_task = animate_logo()
    >>> racer = loop.race(touch_task, animation_task)
    >>> result = await racer

    Note: You should not directly `yield` a `race` instance, see logic in
    `race.__iter__` for explanation.  Always use `await`.
    """

    def __init__(self, *children: AwaitableTask) -> None:
        self.children = children
        self.finished = False
        self.scheduled: list[Task] = []  # scheduled wrapper tasks

    def handle(self, task: Task) -> None:
        """
        Schedule all children Tasks and set `task` as callback.
        """
        finalizer = self._finish
        scheduled = self.scheduled
        self.finished = False

        self.callback = task
        scheduled.clear()

        for child in self.children:
            child_task: Task
            if isinstance(child, _type_gen):
                # child is a coroutine/generator
                # i.e., async function, or function using yield (these are identical
                # in micropython)
                child_task = child
            else:
                # child is a layout -- type-wise, it is an Awaitable, but
                # implementation-wise it is an Iterable and we know that its __iter__
                # will return a Generator.
                child_task = child.__iter__()  # type: ignore [Cannot access attribute "__iter__" for class "Awaitable[Unknown]";;Cannot access attribute "__iter__" for class "Coroutine[Unknown, Unknown, Unknown]"]
            schedule(child_task, None, None, finalizer)
            scheduled.append(child_task)

    def exit(self, except_for: Task | None = None) -> None:
        for task in self.scheduled:
            if task != except_for:
                close(task)

    def _finish(self, task: Task, result: Any) -> None:
        if not self.finished:
            self.finished = True
            self.exit(task)
            schedule(self.callback, result)

    def __iter__(self) -> Task:
        try:
            return (yield self)
        except:  # noqa: E722
            # exception was raised on the waiting task externally with
            # close() or throw(), kill the children tasks and re-raise
            # Make sure finalizers don't continue processing.
            self.finished = True
            self.exit()
            raise


class mailbox(Syscall):
    """
    Wait to receive a value.

    In terms of synchronization primitives, this is a condition variable that also
    contains a value. It is a simplification of Go channels, which is one-ended and
    only has a buffer of size 1.

    The receiving end pauses until a value is received, and then empties the mailbox
    to wait again.

    The sending end synchronously posts a value. It is impossible to wait until
    the value is consumed. Trying to post a value when the mailbox is full raises
    an error, unless `replace=True` is specified

    Example:

    >>> # in task #1:
    >>> box = loop.mailbox()
    >>> while True:
    >>>     result = await box
    >>>     print("awaited result:", result)

    >>> # in task #2:
    >>> box.put("Hello from the other task")
    >>> print("put completed")

    Example Output:

    put completed
    awaited result: Hello from the other task
    """

    _NO_VALUE = object()

    def __init__(self, initial_value: Any = _NO_VALUE) -> None:
        self.value = initial_value
        self.taker: Task | None = None

    def is_empty(self) -> bool:
        """Is the mailbox empty?"""
        return self.value is self._NO_VALUE

    def clear(self) -> None:
        """Empty the mailbox."""
        assert self.taker is None
        self.value = self._NO_VALUE

    def put(self, value: Any, replace: bool = False) -> None:
        """Put a value into the mailbox.

        If there is another task waiting for the value, it will be scheduled to resume.
        Otherwise, the mailbox will hold the value until someone consumes it.

        It is an error to call `put()` when there is a value already held, unless
        `replace` is set to `True`. In such case, the held value is replaced with
        the new one.
        """
        if not self.is_empty() and not replace:
            raise ValueError("mailbox already has a value")

        self.value = value
        if self.taker is not None:
            self._take(self.taker)

    def _take(self, task: Task) -> None:
        """Take a value and schedule the taker."""
        self.taker = None
        schedule(task, self.value)
        self.clear()

    def handle(self, task: Task) -> None:
        assert self.taker is None
        if not self.is_empty():
            self._take(task)
        else:
            self.taker = task

    def __iter__(self) -> Generator:
        assert self.taker is None

        # short-circuit if there is a value already
        if not self.is_empty():
            value = self.value
            self.clear()
            return value

        # otherwise, wait for a value
        try:
            return (yield self)
        finally:
            # Clear the taker even in case of exception. This way stale takers don't
            # blow up someone calling `maybe_close()`
            self.taker = None

    def maybe_close(self) -> None:
        """Shut down the taker if possible."""
        taker = self.taker
        self.taker = None
        if taker is not None and taker is not this_task:
            taker.close()


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

        assert isinstance(task, _type_gen)
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

    def __iter__(self) -> Task:
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
