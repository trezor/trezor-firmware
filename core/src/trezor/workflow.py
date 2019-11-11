from trezor import log, loop

if False:
    from typing import Any, Callable, Optional, Set

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
        start_default(default_constructor)
    if __debug__:
        # In debug builds, we dump a memory info right after a workflow is
        # finished.
        if utils.LOG_MEMORY:
            micropython.mem_info()


def start_default(constructor: Callable[[], loop.Task]) -> None:
    """Start a default workflow, created from `constructor`.

    If a default task is already running, nothing will happen. Use `replace_default`
    to set up a new default task for the next run.
    """
    global default_task
    global default_constructor

    if not default_task:
        default_constructor = constructor
        default_task = constructor()
        if __debug__:
            log.debug(__name__, "start default: %s", default_task)
        # Schedule the default task.  Because the task can complete on its own,
        # we need to reset the `default_task` global in a finalizer.
        loop.schedule(default_task, None, None, _finalize_default)
    else:
        if __debug__:
            log.debug(__name__, "default already started")


def replace_default(constructor: Callable[[], loop.Task]) -> None:
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
                start_default(default_constructor)
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
