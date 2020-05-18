import utime

from trezor import log, loop

if False:
    from typing import Any, Callable, Dict, Optional, Set

    IdleCallback = Callable[[], None]

if __debug__:
    # Used in `on_close` bellow for memory statistics.

    import micropython

    from trezor import utils


# Set of workflow tasks.  Multiple workflows can be running at the same time.
tasks = set()  # type: Set[loop.Task]

# Default workflow task, if a default workflow is running.  Default workflow
# is not contained in the `tasks` set above.
default_task = None  # type: Optional[loop.Task]

# Constructor for the default workflow.  Returns a workflow task.
default_constructor = None  # type: Optional[Callable[[], loop.Task]]


def on_start(workflow: loop.Task) -> None:
    """
    Call after creating a workflow task, but before running it.  You should
    make sure to always call `on_close` when the task is finished.
    """
    # Take note that this workflow task is running.
    if __debug__:
        log.debug(__name__, "start: %s", workflow)
    idle_timer.touch()
    tasks.add(workflow)


def on_close(workflow: loop.Task) -> None:
    """Call when a workflow task has finished running."""
    # Remove task from the running set.
    if __debug__:
        log.debug(__name__, "close: %s", workflow)
    tasks.remove(workflow)
    if not tasks and default_constructor:
        # If no workflows are running, we should create a new default workflow
        # and run it.
        start_default()
    if __debug__:
        # In debug builds, we dump a memory info right after a workflow is
        # finished.
        if utils.LOG_MEMORY:
            micropython.mem_info()


def start_default() -> None:
    """Start a default workflow.

    Use `set_default` to set the default workflow constructor.
    If a default task is already running, nothing will happen.
    """
    global default_task
    global default_constructor

    assert default_constructor is not None

    if not default_task:
        default_task = default_constructor()
        if __debug__:
            log.debug(__name__, "start default: %s", default_task)
        # Schedule the default task.  Because the task can complete on its own,
        # we need to reset the `default_task` global in a finalizer.
        loop.schedule(default_task, None, None, _finalize_default)
    else:
        if __debug__:
            log.debug(__name__, "default already started")


def set_default(constructor: Callable[[], loop.Task]) -> None:
    """Configure a default workflow, which will be started next time it is needed."""
    global default_constructor
    if __debug__:
        log.debug(__name__, "setting a new default: %s", constructor)
    default_constructor = constructor


def kill_default() -> None:
    """Forcefully shut down default task.

    The purpose of the call is to prevent the default task from interfering with
    a synchronous layout-less workflow (e.g., the progress bar in `mnemonic.get_seed`).

    This function should only be called from a workflow registered with `on_start`.
    Otherwise the default will be restarted immediately.
    """
    if default_task:
        if __debug__:
            log.debug(__name__, "close default")
        # We let the `_finalize_default` reset the global.
        loop.close(default_task)


def _finalize_default(task: loop.Task, value: Any) -> None:
    """Finalizer for the default task. Cleans up globals and restarts the default
    in case no other task is running."""
    global default_task

    if default_task is task:
        if __debug__:
            log.debug(__name__, "default closed: %s", task)
        default_task = None

        if not tasks:
            # No registered workflows are running and we are in the default task
            # finalizer, so when this function finished, nothing will be running.
            # We must schedule a new instance of the default now.
            if default_constructor is not None:
                start_default()
            else:
                raise RuntimeError  # no tasks and no default constructor

    else:
        if __debug__:
            log.warning(
                __name__,
                "default task does not match: task=%s, default_task=%s",
                task,
                default_task,
            )


# TODO
# If required, a function `shutdown_default` should be written, that clears the
# default constructor and shuts down the running default task.
# We currently do not need such function, so I'm just noting how it should work.


class IdleTimer:
    """Run callbacks after a period of inactivity.

    A global instance `workflow.idle_timer` is available to create events that fire
    after a specified time of no user or host activity. This instance is kept awake
    by UI taps, swipes, and USB message handling.
    """

    def __init__(self) -> None:
        self.timeouts = {}  # type: Dict[IdleCallback, int]
        self.tasks = {}  # type: Dict[IdleCallback, loop.Task]

    async def _timeout_task(self, callback: IdleCallback) -> None:
        # This function is async, so the result of self._timeout_task() is an awaitable,
        # suitable for scheduling.

        # After the scheduled task completes, self.tasks will contain a stale task
        # object. A new one must be created here so that subsequent calls to touch() can
        # schedule it again.
        self.tasks[callback] = self._timeout_task(callback)
        callback()

    def touch(self) -> None:
        """Wake up the idle timer.

        Events that represent some form of activity (USB messages, touches, etc.) should
        call `touch()` to notify the timer of the activity. All pending callback timers
        will reset.
        """
        for callback, task in self.tasks.items():
            timeout_us = self.timeouts[callback]
            deadline = utime.ticks_add(utime.ticks_us(), timeout_us)
            loop.schedule(task, None, deadline, reschedule=True)

    def set(self, timeout_ms: int, callback: IdleCallback) -> None:
        """Add or update an idle callback.

        Every time `timeout_ms` milliseconds elapse after the last registered activity,
        `callback` will be invoked.
        I.e., in every period of inactivity, each `callback` will only run once. To run
        again, an activity must be registered and then no activity for the specified
        period.

        If `callback` was previously registered, it is updated with a new timeout value.

        `idle_timer.set()` also counts as an activity, so all running idle timers are
        reset.
        """
        # The reason for counting set() as an activity is to clear up an ambiguity that
        # would arise otherwise. This does not matter now, as callbacks are only
        # scheduled during periods of activity.
        # If we ever need to add a callback without touching, we will need to know
        # when this callback should execute (10 mins from now? from last activity? if
        # the latter, what if 10 minutes have already elapsed?)
        if callback in self.tasks:
            loop.close(self.tasks[callback])

        self.timeouts[callback] = timeout_ms * 1000
        self.tasks[callback] = self._timeout_task(callback)
        self.touch()

    def remove(self, callback: IdleCallback) -> None:
        """Remove an idle callback."""
        self.timeouts.pop(callback, None)
        task = self.tasks.pop(callback, None)
        if task is not None:
            loop.close(task)


"""Global idle timer."""
idle_timer = IdleTimer()
