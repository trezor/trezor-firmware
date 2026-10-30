from micropython import const
from typing import TYPE_CHECKING

import trezorui_api
from trezor import io, loop
from trezor.ui import Shutdown
from trezor.ui.library import CANCELLED, run
from trezor.ui.library.fields import set_data_puller
from trezor.wire import ActionCancelled, context
from trezor.wire.errors import DataError, Error

from .session import SERVICE_UI

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from trezorio import IpcMessage

    from .session import Session

# Message id of a chunk request on the UI service, as the app-side shim reads it.
_MSG_ID_CHUNK = const(1)
# Message id of a chunk the app's source could not produce: core stops the
# layout, and the app turns that cancel into the source's own error.
_MSG_ID_CHUNK_FAILED = const(2)

# how long Core waits for the app's next chunk
_IPC_TIMEOUT_MS = const(20000)


async def handle(session: Session, msg: IpcMessage) -> None:
    """Show the screen the app asked for and send the app the person's answer."""
    set_data_puller(_data_puller(session))
    try:
        result = await run(
            trezorui_api.deserialize_ui_message(data=bytes(msg.data)),
            session.app_id,
        )
    except ActionCancelled:
        result = CANCELLED
    except (
        Error,
        MemoryError,
        loop.TaskClosed,
        Shutdown,
        context.UnexpectedMessageException,
    ):
        # The workflow's own control flow, such as the host cancelling while
        # the screen is up: not the app's request at fault, so it goes on up
        # as `run.py` passes it on.
        raise
    except Exception as e:
        # The request cannot be drawn. Answering would leave the app waiting on
        # a screen that never existed, so the app stops.
        session.die(DataError(f"Cannot show the app's screen: {e}"))
    finally:
        set_data_puller(None)
    if __debug__:
        log.debug(__name__, f"UI interaction result: {result}")

    try:
        # Only a decision is an answer. Anything else a layout ends with is a
        # bug, never a yes, and the app stops.
        answer = trezorui_api.encode_ui_result(result=result)
    except Exception as e:
        session.die(DataError(f"Unexpected layout result: {e}"))
    try:
        session.send(SERVICE_UI, 0, answer)
    except Exception as e:
        session.die(DataError(f"Cannot send the screen's answer: {e}"))


def _data_puller(
    session: Session,
) -> "Callable[[int, int, int], Awaitable[bytes]]":
    """The driver's way to ask the app for a `Data` chunk.

    Core sends the range it wants and the app answers with those bytes, or says
    the source could not produce them and stops the layout. The app's own bytes
    never leave its memory in full, and the answer doubles as the wait for core's
    next request or its decision.
    """

    async def pull(field: int, offset: int, length: int) -> bytes:
        session.send(
            SERVICE_UI,
            _MSG_ID_CHUNK,
            trezorui_api.encode_chunk_request(
                field=field, offset=offset, length=length
            ),
        )
        msg = await loop.wait(io.IPC2_EVENT | io.POLL_READ, timeout_ms=_IPC_TIMEOUT_MS)
        if msg.service != SERVICE_UI:
            session.die(DataError("Unexpected message while pulling data"))
        if msg.message_id == _MSG_ID_CHUNK_FAILED:
            raise ActionCancelled
        if msg.message_id != _MSG_ID_CHUNK:
            session.die(DataError("Unexpected message while pulling data"))
        # The app's `ipc_call` is still waiting; core's next message — another
        # request, or the decision — is its answer.
        return bytes(msg.data)

    return pull
