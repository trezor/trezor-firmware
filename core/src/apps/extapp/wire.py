from typing import TYPE_CHECKING

from trezor.messages import ExtAppMessage, ExtAppResponse
from trezor.wire import context
from trezor.wire.errors import DataError, Error

from .session import SERVICE_WIRE_CONTINUE

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from trezorio import IpcMessage
    from typing import NoReturn

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
    if ack.message_id > 0xFFFF:
        session.die(DataError("Invalid message ID."))
    try:
        session.send(SERVICE_WIRE_CONTINUE, ack.message_id, ack.data)
    except Exception:
        # e.g. the message does not fit the app's inbox; the app would keep
        # waiting for it, so stop the app instead
        session.die(DataError("Failed to send host message to app"))


def handle_error(msg: IpcMessage) -> NoReturn:
    """Fail the request with the app's error; the app then waits for the
    host's next request."""
    err_message = (
        msg.data.decode("utf-8", "replace")
        if isinstance(msg.data, (bytes, bytearray))
        else str(msg.data)
    )
    if __debug__:
        log.debug(__name__, f"Received wire error message: {err_message}")
    raise Error(msg.message_id, err_message)  # pyright: ignore [reportArgumentType]
