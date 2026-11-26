from typing import TYPE_CHECKING

from trezor import io, loop
from trezor.ui import modui
from trezor.wire import ActionCancelled
from trezormodui import (
    AMOUNT,
    CONFIRM,
    DANGER,
    DETAILS,
    MSG_CHUNK,
    MSG_CHUNK_FAILED,
    MSG_DECISION,
    REQUEST_DONE,
    REQUEST_REVIEW,
    REQUEST_VERIFY_ADDRESS,
    REQUEST_VERIFY_PUBKEY,
    RESULT_CANCELLED,
    RESULT_CONFIRMED,
    RESULT_SHOW_DETAILS,
    STRONG,
    TEXT_SOURCE,
    deserialize_ui_message,
    encode_chunk_request,
    encode_ui_result,
)

from .session import IPC_TIMEOUT_MS, SERVICE_UI

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from trezorio import IpcMessage

    from trezor.ui.modui.pages import Field

    from .session import Session


async def handle(session: Session, msg: IpcMessage) -> None:
    """Show the screen the app asked for and send the app the person's answer.

    A refusal is an answer. Anything else that goes wrong goes up to `run.py`,
    which stops the app: it would otherwise wait on a screen that never came.
    """
    try:
        result = await _show(session, deserialize_ui_message(data=bytes(msg.data)))
    except ActionCancelled:
        result = RESULT_CANCELLED
    if __debug__:
        log.debug(__name__, f"UI interaction result: {result}")

    session.send(SERVICE_UI, MSG_DECISION, encode_ui_result(result=result))
    if session.progress is not None:
        # The screen covered the bar while the person decided; show it again.
        session.progress.report(session.progress.value, session.progress_label)


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
    elif kind == REQUEST_VERIFY_PUBKEY:
        await modui.verify_pubkey(name, *args)
    elif kind == REQUEST_DONE:
        (text,) = args
        await modui.done(name, text)
    else:
        raise ValueError(f"Unknown UI request kind {kind}")
    return RESULT_CONFIRMED


def _fields(session: Session, fields: list, first: int) -> "list[Field]":
    """The request's facts as `modui` takes them. `first` is the flat index of
    the first one."""
    result = []
    for index, (kind, label, value, ticker) in enumerate(fields, first):
        if kind == AMOUNT:
            result.append(modui.amount(label, value, ticker))
        elif kind == TEXT_SOURCE:
            result.append(modui.text_source(label, value, _pull(session, index)))
        else:
            result.append((kind, label, value))
    return result


def _pull(session: Session, field: int) -> "Callable[[int, int], Awaitable[bytes]]":
    """How the driver reads the text of the app's `text_source` field at `field`.

    Core sends the range it wants and the app answers with exactly those bytes,
    or says its source could not produce them and the screen stops. The app's
    text never leaves its memory in full, and the answer doubles as the wait
    for core's next request or its decision.
    """

    async def pull(offset: int, length: int) -> bytes:
        session.send(
            SERVICE_UI,
            MSG_CHUNK,
            encode_chunk_request(field=field, offset=offset, length=length),
        )
        msg = await loop.wait(io.IPC2_EVENT | io.POLL_READ, timeout_ms=IPC_TIMEOUT_MS)
        # Only the chunk can come here. `run._serve` is parked in `handle` until
        # the review is decided, and an app has one call in flight at a time, so
        # a message for another service is the app's source calling out from
        # inside this call.
        if msg.service != SERVICE_UI:
            session.die("Unexpected message while pulling text")
        if msg.message_id == MSG_CHUNK_FAILED:
            raise ActionCancelled
        if msg.message_id != MSG_CHUNK:
            session.die("Unexpected message while pulling text")
        if len(msg.data) != length:
            session.die("Wrong chunk size while pulling text")
        # The app's `ipc_call` is still waiting; core's next message - another
        # request, or the decision - is its answer.
        return bytes(msg.data)

    return pull
