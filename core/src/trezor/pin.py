from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    from trezor.ui.layouts.common import ProgressLayout

_previous_seconds: int | None = None
_previous_remaining: str | None = None
_progress_layout: ProgressLayout | None = None
_started_with_empty_loader = False
keepalive_callback: Any = None

_ignore_loader_messages: tuple[str, ...] = ()


def ignore_nonpin_loader_messages() -> None:
    global _ignore_loader_messages
    _ignore_loader_messages = ("Processing", "Starting up")


def allow_all_loader_messages() -> None:
    global _ignore_loader_messages
    _ignore_loader_messages = ()


def render_empty_loader(message: str, description: str) -> None:
    """Render empty loader to prevent the screen appear to be frozen."""
    from trezor.ui.layouts.progress import pin_progress

    global _progress_layout
    global _started_with_empty_loader

    _progress_layout = pin_progress(message, description)
    _progress_layout.report(0, None)

    _started_with_empty_loader = True


def show_pin_timeout(seconds: int, progress: int, message: str) -> bool:
    from trezor.ui.layouts.progress import pin_progress

    # Possibility to ignore certain messages - not showing loader for them
    if message in _ignore_loader_messages:
        return False

    global _previous_seconds
    global _previous_remaining
    global _progress_layout
    global _started_with_empty_loader

    if callable(keepalive_callback):
        keepalive_callback()

    if progress == 0 or _progress_layout is None:
        _previous_seconds = None

    if seconds != _previous_seconds:
        if seconds == 0:
            remaining = "Done"
        elif seconds == 1:
            remaining = "1 second left"
        else:
            remaining = f"{seconds} seconds left"
        _previous_remaining = remaining
        _previous_seconds = seconds
    else:
        remaining = _previous_remaining

    # create the layout if it doesn't exist yet or should be started again
    if _progress_layout is None or (progress == 0 and not _started_with_empty_loader):
        _progress_layout = pin_progress(message, description=remaining or "")

    # reset the flag - the render_empty_loader() has the effect only in the first call
    # of this function, where we do not want to re-initialize the layout
    # to avoid a screen flicker
    _started_with_empty_loader = False

    # update the progress layout
    _progress_layout.report(progress, remaining)

    # drop the layout when done so trezor.ui doesn't have to remain in memory
    if progress >= 1000:
        _progress_layout = None

    return False
