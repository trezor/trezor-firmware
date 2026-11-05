from micropython import const
from typing import TYPE_CHECKING

import trezormodui
from trezor import io, loop
from trezor.ui import Shutdown, modui
from trezor.wire import ActionCancelled, context
from trezor.wire.errors import DataError, Error
from trezormodui import (
    AMOUNT,
    CONFIRM,
    DANGER,
    DATA,
    DETAILS,
    REQUEST_DONE,
    REQUEST_REVIEW,
    REQUEST_VERIFY_ADDRESS,
    REQUEST_VERIFY_PUBKEY,
    RESULT_CANCELLED,
    RESULT_CONFIRMED,
    RESULT_SHOW_DETAILS,
    STRONG,
)

from .session import SERVICE_UI

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from trezorio import IpcMessage

    from trezor.ui.modui.pages import Field

    from .session import Session

# how long Core waits for the app's next chunk
_IPC_TIMEOUT_MS = const(20000)


async def handle(session: Session, msg: IpcMessage) -> None:
    """Show the screen the app asked for and send the app the person's answer."""
    try:
        result = await _show(
            session, trezormodui.deserialize_ui_message(data=bytes(msg.data))
        )
    except ActionCancelled:
        result = RESULT_CANCELLED
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
        session.send(
            SERVICE_UI,
            trezormodui.MSG_DECISION,
            trezormodui.encode_ui_result(result=result),
        )
    except Exception as e:
        session.die(DataError(f"Cannot send the screen's answer: {e}"))
    if session.progress is not None:
        # The screen covered the bar while the person decided; show it again.
        # Reporting the current value leaves the label alone and only repaints.
        session.progress.report(session.progress.value)


async def _show(session: Session, request: tuple) -> int:
    """Run the request with `trezor.ui.modui` and return the decision for the app.

    The step reaches the host prefixed with the app's identity, its image ID
    (`testapp.trezor.io`), so an app names its steps alone.
    """
    kind, step, *args = request
    name = f"{session.app_id}/{step}"

    if kind == REQUEST_REVIEW:
        title, fields, extras, answer = args
        # A `data` field is pulled by its flat index: the review's own fields
        # first, then each extra's, in order.
        index = len(fields)
        offered = []
        for label, extra_fields in extras:
            offered.append(modui.Extra(label, _fields(session, extra_fields, index)))
            index += len(extra_fields)
        review = modui.review(name, title, _fields(session, fields, 0)).extras(offered)
        if answer == CONFIRM:
            await review.confirm()
        elif answer == STRONG:
            await review.confirm_strong()
        elif answer == DANGER:
            await review.confirm_danger()
        elif answer == DETAILS:
            return RESULT_SHOW_DETAILS if await review.details() else RESULT_CONFIRMED
        else:
            raise ValueError(f"Unknown review answer {answer}")
        return RESULT_CONFIRMED

    if kind == REQUEST_VERIFY_ADDRESS:
        await modui.verify_address(name, *args)
        return RESULT_CONFIRMED
    if kind == REQUEST_VERIFY_PUBKEY:
        await modui.verify_pubkey(name, *args)
        return RESULT_CONFIRMED
    if kind == REQUEST_DONE:
        (text,) = args
        await modui.done(name, text)
        return RESULT_CONFIRMED

    raise ValueError(f"Unknown UI request kind {kind}")


def _fields(session: Session, fields: list, first: int) -> "list[Field]":
    """The request's facts as `modui` takes them. `first` is the flat index of
    the first one."""
    result = []
    for index, (kind, label, value, ticker) in enumerate(fields, first):
        if kind == AMOUNT:
            result.append(modui.amount(label, value, ticker))
        elif kind == DATA:
            result.append(modui.data_source(label, value, _pull(session, index)))
        else:
            result.append((kind, label, value))
    return result


def _pull(session: Session, field: int) -> "Callable[[int, int], Awaitable[bytes]]":
    """How the driver reads the bytes of the app's `data` field at `field`.

    Core sends the range it wants and the app answers with those bytes, or says
    its source could not produce them and the screen stops. The app's bytes
    never leave its memory in full, and the answer doubles as the wait for
    core's next request or its decision.
    """

    async def pull(offset: int, length: int) -> bytes:
        session.send(
            SERVICE_UI,
            trezormodui.MSG_CHUNK,
            trezormodui.encode_chunk_request(field=field, offset=offset, length=length),
        )
        msg = await loop.wait(io.IPC2_EVENT | io.POLL_READ, timeout_ms=_IPC_TIMEOUT_MS)
        if msg.service != SERVICE_UI:
            session.die(DataError("Unexpected message while pulling data"))
        if msg.message_id == trezormodui.MSG_CHUNK_FAILED:
            raise ActionCancelled
        if msg.message_id != trezormodui.MSG_CHUNK:
            session.die(DataError("Unexpected message while pulling data"))
        # The app's `ipc_call` is still waiting; core's next message - another
        # request, or the decision - is its answer.
        return bytes(msg.data)

    return pull
