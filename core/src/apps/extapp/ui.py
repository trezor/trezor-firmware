from typing import TYPE_CHECKING

import trezorui_api
from trezor import loop
from trezor.ui import Shutdown
from trezor.ui.library import CANCELLED, run
from trezor.wire import ActionCancelled, context
from trezor.wire.errors import DataError, Error

from .session import SERVICE_UI

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from trezorio import IpcMessage

    from .session import Session


async def handle(session: Session, msg: IpcMessage) -> None:
    """Show the screen the app asked for and send the app the person's answer."""
    try:
        result = await run(
            trezorui_api.deserialize_ui_message(data=bytes(msg.data)),
            session.app_name,
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
