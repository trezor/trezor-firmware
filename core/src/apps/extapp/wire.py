from typing import TYPE_CHECKING

from trezor.messages import ExtAppMessage, ExtAppResponse, Failure
from trezor.wire import context
from trezor.wire.errors import DataError

from .session import SERVICE_WIRE_CONTINUE, SERVICE_WIRE_START

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from trezorio import IpcMessage

    from .session import Session


def end(msg: IpcMessage) -> ExtAppResponse:
    """The app's final response, returned to the host as the workflow result."""
    if __debug__:
        log.debug(__name__, f"Forwarding wire end message: {msg.message_id}")
    return ExtAppResponse(message_id=msg.message_id, data=msg.data, finished=True)


async def handle_continue(session: Session, msg: IpcMessage) -> None:
    """Forward an intermediate response to the host and pass its ack to the app."""
    response = ExtAppResponse(message_id=msg.message_id, data=msg.data, finished=False)
    ack = await context.call(response, ExtAppMessage)
    _forward_ack(session, SERVICE_WIRE_CONTINUE, ack)


async def handle_error(session: Session, msg: IpcMessage) -> None:
    """Send the app's error to the host as a `Failure` and restart the app
    with the host's next message."""
    err_message = (
        msg.data.decode("utf-8", "replace")
        if isinstance(msg.data, (bytes, bytearray))
        else str(msg.data)
    )
    if __debug__:
        log.debug(__name__, f"Received wire error message: {err_message}")
    response = Failure(
        code=msg.message_id,  # pyright: ignore [reportArgumentType]
        message=err_message,
    )
    ack = await context.call(response, ExtAppMessage)
    _forward_ack(session, SERVICE_WIRE_START, ack)


def _forward_ack(session: Session, service: int, ack: ExtAppMessage) -> None:
    if ack.message_id > 0xFFFF:
        session.die(DataError("Invalid message ID."))
    try:
        session.send(service, ack.message_id, ack.data)
    except Exception:
        # e.g. the message does not fit the app's inbox; the app would keep
        # waiting for it, so stop the app instead
        session.die(DataError("Failed to send host message to app"))
