from typing import TYPE_CHECKING

from trezor.messages import ExtAppMessage, ExtAppResponse
from trezor.wire import context
from trezor.wire.errors import DataError, Error

from .session import SERVICE_WIRE_CONTINUE

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
    """End the request with the app's error, sent to the host as a `Failure`.

    A failure ends the request, like a final response does. Waiting here for
    the host's next message would keep the workflow alive, so the homescreen
    would never come back. The app is already waiting for its next request,
    which the next `run()` delivers.
    """
    err_message = (
        msg.data.decode("utf-8", "replace")
        if isinstance(msg.data, (bytes, bytearray))
        else str(msg.data)
    )
    if __debug__:
        log.debug(__name__, f"Received wire error message: {err_message}")
    raise Error(
        msg.message_id,  # pyright: ignore [reportArgumentType]
        err_message,
    )


def _forward_ack(session: Session, service: int, ack: ExtAppMessage) -> None:
    if ack.message_id > 0xFFFF:
        session.die(DataError("Invalid message ID."))
    session.send(service, ack.message_id, ack.data)
