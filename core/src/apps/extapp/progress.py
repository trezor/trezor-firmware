from typing import TYPE_CHECKING

import trezorui_api
from trezor.ui.layouts.progress import progress
from trezor.wire.errors import DataError

from .session import SERVICE_PROGRESS

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from trezorio import IpcMessage

    from .session import Session

_INIT = 0
_STEP = 1
_LABEL = 2
_STOP = 3


def handle(session: Session, msg: IpcMessage) -> None:
    """Drive the progress layout on the app's behalf and acknowledge each step."""
    message_id = msg.message_id
    if __debug__:
        log.debug(__name__, f"Processing progress message: {message_id}")
    obj = trezorui_api.deserialize_progress_message(data=bytes(msg.data))

    if message_id == _INIT:
        label, total = obj
        session.progress_total = total
        session.progress_done = 0
        # A total of 0 means the app does not know it: motion, no fill.
        session.progress = progress(description=label, indeterminate=total == 0)
        # The layout only appears on its first report, and an indeterminate
        # progress never reports: show it now.
        session.progress.report(0)
    elif message_id == _STEP:
        if session.progress is None:
            session.die(DataError("Progress not initialized"))
        total = session.progress_total
        if total:
            # Past the total pins the bar full rather than wrapping.
            session.progress_done = min(session.progress_done + obj, total)
            session.progress.report(session.progress_done * 1000 // total)
    elif message_id == _LABEL:
        if session.progress is None:
            session.die(DataError("Progress not initialized"))
        # The label changes under the bar; the fill and the count are ours.
        session.progress.report(session.progress.value, description=obj)
    elif message_id == _STOP:
        if session.progress is None:
            session.die(DataError("Progress not initialized"))
        session.progress.stop()
        session.progress = None
    else:
        session.die(DataError("Unknown progress message ID"))

    try:
        session.send(SERVICE_PROGRESS, message_id, b"")
    except Exception:
        session.die(DataError("Failed to send progress result"))
