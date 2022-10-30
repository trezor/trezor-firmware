from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any
    from trezor.ui.layouts.common import ProgressLayout

_previous_seconds: int | None = None
_previous_remaining: str | None = None
_progress_layout: ProgressLayout | None = None
keepalive_callback: Any = None


def show_pin_timeout(seconds: int, progress: int, message: str) -> bool:
    from trezor.ui.layouts import pin_progress

    global _previous_seconds
    global _previous_remaining
    global _progress_layout

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

    if progress == 0 or _progress_layout is None:
        _progress_layout = pin_progress(message, description=remaining or "")
    _progress_layout.report(progress, remaining)
    # drop the layout when done so trezor.ui doesn't have to remain in memory
    if seconds == 0:
        _progress_layout = None

    return False
