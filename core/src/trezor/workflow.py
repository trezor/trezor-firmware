from trezor import loop

if False:
    from typing import Callable, Optional, Set

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
    """Start a default workflow, created from `constructor`."""
    global default_task
    global default_constructor

    if not default_task:
        default_constructor = constructor
        default_task = constructor()
        loop.schedule(default_task)


def close_default() -> None:
    """Explicitly close the default workflow task."""
    global default_task

    if default_task:
        loop.close(default_task)
        default_task = None
