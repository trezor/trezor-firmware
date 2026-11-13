from typing import TYPE_CHECKING

from trezor.enums import FailureType
from trezor.messages import ExtAppResponse
from trezor.wire import context
from trezor.wire.errors import DataError, Error

from .session import SERVICE_WIRE

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from trezorio import IpcMessage
    from typing import NoReturn

    from trezor.messages import ExtAppMessage

    from .session import Session

# failure codes an app may report, indexed by the SDK's `FailureKind`
_APP_FAILURE_CODES = (
    FailureType.DataError,
    FailureType.ActionCancelled,
    FailureType.ProcessError,
)


async def handle(session: Session, msg: IpcMessage) -> None:
    """Forward the app's message to the host."""
    if __debug__:
        log.debug(__name__, f"Forwarding wire message: {msg.message_id}")
    response = ExtAppResponse(message_id=msg.message_id, data=msg.data)
    await context.get_context().write(response)
    session.response_sent = True


def final_response(session: Session, msg: IpcMessage) -> ExtAppResponse:
    """The response of an app that has exited, to be returned as the workflow
    result."""
    if __debug__:
        log.debug(__name__, f"Final wire message: {msg.message_id}")
    session.response_sent = True
    return ExtAppResponse(message_id=msg.message_id, data=msg.data)


def handle_host_message(session: Session, msg: ExtAppMessage) -> None:
    """Forward the host's message to the app."""
    if msg.instance_id != session.instance_id:
        raise DataError("Invalid instance ID")
    if msg.message_id > 0xFFFF:
        # the host's fault, not the app's
        session.die("Invalid message ID from host", DataError("Invalid message ID"))
    session.response_sent = False
    try:
        session.send(SERVICE_WIRE, msg.message_id, msg.data)
    except Exception:
        # e.g. the message does not fit the app's inbox; the app would keep
        # waiting for it, so stop the app instead
        session.die("Failed to send host message to app")


def handle_error(session: Session, msg: IpcMessage) -> NoReturn:
    """Fail the request with the app's error."""
    err_message = (
        msg.data.decode("utf-8", "replace")
        if isinstance(msg.data, (bytes, bytearray))
        else str(msg.data)
    )
    if __debug__:
        log.debug(__name__, f"Received wire error message: {err_message}")
    if msg.message_id >= len(_APP_FAILURE_CODES):
        session.die(f"Invalid failure kind {msg.message_id}")
    raise Error(_APP_FAILURE_CODES[msg.message_id], err_message)
