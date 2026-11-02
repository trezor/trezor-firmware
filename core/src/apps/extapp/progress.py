from typing import TYPE_CHECKING

from trezor.ui.layouts.progress import progress
from trezormodui import (
    PROGRESS_END,
    PROGRESS_INIT,
    PROGRESS_LABEL,
    PROGRESS_STEP,
    deserialize_progress_message,
)

from .session import SERVICE_PROGRESS

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from trezorio import IpcMessage

    from .session import Session


def handle(session: Session, msg: IpcMessage) -> None:
    """Drive the progress layout on the app's behalf and acknowledge each step."""
    message_id = msg.message_id
    if __debug__:
        log.debug(__name__, f"Processing progress message: {message_id}")
    obj = deserialize_progress_message(data=bytes(msg.data))

    if message_id == PROGRESS_INIT:
        if session.progress is not None:
            # One bar at a time: a start while one is open is the app's mistake.
            session.die("Nested progress")
        label, total = obj
        session.progress_label = label
        session.progress_total = total
        session.progress_done = 0
        # A total of 0 means the app does not know it: motion, no fill.
        session.progress = progress(description=label, indeterminate=total == 0)
        # The layout only appears on its first report, and an indeterminate
        # progress never reports: show it now.
        session.progress.report(0, label)
    else:
        if session.progress is None:
            session.die("Progress not initialized")
        if message_id == PROGRESS_STEP:
            total = session.progress_total
            if total:
                # Past the total pins the bar full rather than wrapping.
                session.progress_done = min(session.progress_done + obj, total)
                session.progress.report(
                    session.progress_done * 1000 // total, session.progress_label
                )
        elif message_id == PROGRESS_LABEL:
            # Every report carries the label, so the bar keeps it; the model
            # draws it with the next report that moves the bar.
            session.progress_label = obj
            session.progress.report(session.progress.value, obj)
        elif message_id == PROGRESS_END:
            session.progress.stop()
            session.progress = None
        else:
            session.die("Unknown progress message ID")

    session.send(SERVICE_PROGRESS, message_id, b"")
