import utime

import storage.cache
from trezor import log, loop

if False:
    from typing import Callable

    IdleCallback = Callable[[], None]

if __debug__:
    # Used in `on_close` bellow for memory statistics.

    import micropython

    from trezor import utils


# Set of workflow tasks.  Multiple workflows can be running at the same time.
tasks: set[loop.spawn] = set()

# Default workflow task, if a default workflow is running.  Default workflow
# is not contained in the `tasks` set above.
default_task: loop.spawn | None = None

# Constructor for the default workflow.  Returns a workflow task.
default_constructor: Callable[[], loop.Task] | None = None


def _on_start(workflow: loop.spawn) -> None:
    """
    Called after creating a workflow task, but before running it.
    """
    # Take note that this workflow task is running.
    if __debug__:
        log.debug(__name__, "start: %s", workflow.task)
    idle_timer.touch()
    tasks.add(workflow)


def _on_close(workflow: loop.spawn) -> None:
    """Called when a workflow task has finished running."""
    # Remove task from the running set.
    if __debug__:
        log.debug(__name__, "close: %s", workflow.task)
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


def spawn(workflow: loop.Task) -> loop.spawn:
    """Spawn a workflow task.

    Creates an instance of loop.spawn for the workflow and registers it into the
    workflow management system.
    """
    task = loop.spawn(workflow)
    _on_start(task)
    task.set_finalizer(_on_close)
    return task


def start_default() -> None:
    """Start a default workflow.

    Use `set_default` to set the default workflow constructor.
    If a default task is already running, nothing will happen.
    """
    global default_task
    global default_constructor

    assert default_constructor is not None

    if not default_task:
        default_task = loop.spawn(default_constructor())
        if __debug__:
            log.debug(__name__, "start default: %s", default_task.task)
        default_task.set_finalizer(_finalize_default)
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
        default_task.close()


def close_others() -> None:
    """Request workflow (and UI) exclusivity: shut down all running tasks, except
    the one that is currently executing.

    If this is called from outside a registered workflow, it is equivalent to "close
    all tasks". In that case, the default task will be restarted afterwards.
    """
    if default_task is not None and not default_task.is_running():
        default_task.close()
        # if no other tasks are running, start_default will run immediately

    # we need a local copy of tasks because processing task.close() modifies
    # the global instance
    for task in list(tasks):
        if not task.is_running():
            task.close()

    storage.cache.homescreen_shown = None

    # if tasks were running, closing the last of them will run start_default


def _finalize_default(task: loop.spawn) -> None:
    """Finalizer for the default task. Cleans up globals and restarts the default
    in case no other task is running."""
    global default_task

    assert default_task is task  # finalizer is closing something other than default?
    assert default_constructor is not None  # it should always be configured

    if __debug__:
        log.debug(__name__, "default closed: %s", task.task)
    default_task = None

    if not tasks:
        # No registered workflows are running and we are in the default task
        # finalizer, so when this function finished, nothing will be running.
        # We must schedule a new instance of the default now.
        start_default()


class IdleTimer:
    """Run callbacks after a period of inactivity.

    A global instance `workflow.idle_timer` is available to create events that fire
    after a specified time of no user or host activity. This instance is kept awake
    by UI taps, swipes, and USB message handling.
    """

    def __init__(self) -> None:
        self.timeouts: dict[IdleCallback, int] = {}
        self.tasks: dict[IdleCallback, loop.Task] = {}

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
            deadline = utime.ticks_add(utime.ticks_ms(), timeout_us)
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

        self.timeouts[callback] = timeout_ms
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
