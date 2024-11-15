import utime
from typing import TYPE_CHECKING

import storage.cache as storage_cache
from trezor import log, loop
from trezor.enums import MessageType

if TYPE_CHECKING:
    from typing import Callable

    IdleCallback = Callable[[], None]

if __debug__:
    # Used in `on_close` below for memory statistics.

    import micropython

    from trezor import utils


ALLOW_WHILE_LOCKED = (
    MessageType.Initialize,
    MessageType.EndSession,
    MessageType.GetFeatures,
    MessageType.Cancel,
    MessageType.LockDevice,
    MessageType.DoPreauthorized,
    MessageType.WipeDevice,
    MessageType.SetBusy,
    MessageType.Ping,
)


# Set of workflow tasks.  Multiple workflows can be running at the same time.
tasks: set[loop.spawn] = set()

# Default workflow task, if a default workflow is running.  Default workflow
# is not contained in the `tasks` set above.
default_task: loop.spawn | None = None

# Constructor for the default workflow.  Returns a workflow task.
default_constructor: Callable[[], loop.Task] | None = None

# Determines whether idle timer firing closes currently running workflow. Storage is locked always.
autolock_interrupts_workflow: bool = True


def _on_start(workflow: loop.spawn) -> None:
    """
    Called after creating a workflow task, but before running it.
    """
    # Take note that this workflow task is running.
    if __debug__:
        log.debug(__name__, "start: %s", workflow.task)
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
    global autolock_interrupts_workflow

    assert default_constructor is not None

    if not default_task:
        default_task = loop.spawn(default_constructor())
        if __debug__:
            log.debug(__name__, "start default: %s", default_task.task)
        default_task.set_finalizer(_finalize_default)
    else:
        if __debug__:
            log.debug(__name__, "default already started")

    autolock_interrupts_workflow = True


def set_default(constructor: Callable[[], loop.Task], restart: bool = False) -> None:
    """Configure a default workflow, which will be started next time it is needed."""
    global default_constructor
    if __debug__:
        log.debug(__name__, "setting a new default: %s", constructor)
    default_constructor = constructor
    if restart:
        # XXX should this be the default (or only) behavior?
        kill_default()


def kill_default() -> None:
    """Forcefully shut down default task.

    If called while a workflow is running, the default task is stopped. This can be used
    to prevent the default task from interfering with a synchronous layout-less workflow
    (e.g., the progress bar in `mnemonic.get_seed`).

    If called when no workflow is running, the default task will automatically be
    restarted. This can be used to replace the default with a different workflow.
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

    storage_cache.homescreen_shown = None

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
    by UI taps, swipes, and DebugLinkDecision message.
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

    def touch(self, _restore_from_cache: bool = False) -> None:
        """Wake up the idle timer.

        Events that represent some form of activity (touches, etc.) should call `touch()`
        to notify the timer of the activity. All pending callback timers will reset.

        If `_restore_from_cache` is True the function attempts to use previous
        timestamp stored in storage.cache. If the parameter is False or no
        deadline is saved, the function computes new deadline based on current
        time and saves it to storage.cache. This is done to avoid losing an
        active timer when workflow restart happens and tasks are lost.
        """
        if _restore_from_cache and storage_cache.autolock_last_touch is not None:
            now = storage_cache.autolock_last_touch
        else:
            now = utime.ticks_ms()
        storage_cache.autolock_last_touch = now

        for callback, task in self.tasks.items():
            timeout_us = self.timeouts[callback]
            deadline = utime.ticks_add(now, timeout_us)
            loop.schedule(task, None, deadline, reschedule=True)

    def set(self, timeout_ms: int, callback: IdleCallback) -> None:
        """Add or update an idle callback.

        Every time `timeout_ms` milliseconds elapse after the last registered activity,
        `callback` will be invoked.
        I.e., in every period of inactivity, each `callback` will only run once. To run
        again, an activity must be registered and then no activity for the specified
        period.

        If `callback` was previously registered, it is updated with a new timeout value.

        If there is last activity timestamp saved in `storage.cache` then
        `idle_timer.set()` uses it to calculate timer deadlines. Otherwise current
        timestamp is used, resetting any idle timers.
        """
        if callback in self.tasks:
            loop.close(self.tasks[callback])

        self.timeouts[callback] = timeout_ms
        self.tasks[callback] = self._timeout_task(callback)
        self.touch(_restore_from_cache=True)

    def remove(self, callback: IdleCallback) -> None:
        """Remove an idle callback."""
        self.timeouts.pop(callback, None)
        task = self.tasks.pop(callback, None)
        if task is not None:
            loop.close(task)


idle_timer = IdleTimer()
"""Global idle timer."""
