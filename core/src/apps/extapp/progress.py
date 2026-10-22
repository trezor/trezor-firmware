from micropython import const
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

_INIT = const(0)
_REPORT = const(1)
_STOP = const(2)


def handle(session: Session, msg: IpcMessage) -> None:
    """Drive the progress layout on the app's behalf and acknowledge each step."""
    message_id = msg.message_id
    if __debug__:
        log.debug(__name__, f"Processing progress message: {message_id}")
    obj = trezorui_api.deserialize_progress_message(data=bytes(msg.data))

    if message_id == _INIT:
        description, title, indeterminate, danger = obj
        session.progress = progress(
            description=description,
            title=title,
            indeterminate=indeterminate,
            danger=danger,
        )
    elif message_id == _REPORT:
        if session.progress is None:
            session.die(DataError("Progress not initialized"))
        description, value = obj
        session.progress.report(value, description=description)
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
