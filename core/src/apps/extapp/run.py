from micropython import const
from typing import TYPE_CHECKING

import ustruct  # pyright: ignore[reportMissingImports]
from storage import cache_common as cc
from trezor import TR, app, io, loop
from trezor.ui import Shutdown as ui_shutdown
from trezor.ui.layouts import error_popup, interact_simple
from trezor.wire import context
from trezor.wire.errors import DataError, Error, FirmwareError

from apps.common import paths

from . import crypto, progress, ui, wire
from .session import (
    SERVICE_CRYPTO,
    SERVICE_PROGRESS,
    SERVICE_UI,
    SERVICE_WIRE_CONTINUE,
    SERVICE_WIRE_END,
    SERVICE_WIRE_ERROR,
    SERVICE_WIRE_START,
    Session,
)

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from trezorio import IpcMessage

    from trezor.messages import ExtAppMessage, ExtAppResponse

# The apps' allowed path patterns hardcode their coin type, so the SLIP-44 ID
# only fills unused placeholders; 1 is the testnet ID.
_SLIP44_ID = const(1)

# how long the error screen stays up before the app's failure is reported
_ERROR_POPUP_TIMEOUT_MS = const(2000)

# how long Core waits for the app's next IPC message
_IPC_TIMEOUT_MS = const(20000)


async def run(request: ExtAppMessage) -> ExtAppResponse:
    """Forward `request` to the running app and serve its IPC requests until
    it sends its final response."""
    session = _open_session(request)
    try:
        return await _serve(session, request)
    except Exception as e:
        if not session.dead:
            raise
        await _show_error(session, e)
        raise


def _describe(exception: BaseException) -> str:
    """Text of `exception`, falling back to its type when it has none."""
    # `wire.Error` keeps its text in `.message`, its `str()` is empty
    message = getattr(exception, "message", None) or str(exception)
    return message or exception.__class__.__name__


async def _show_error(session: Session, exception: Exception) -> None:
    """Briefly show why the app was stopped."""
    try:
        if session.progress is not None:
            session.progress.stop()
            session.progress = None
        # passed as a parameter so braces in the message aren't format fields
        with error_popup(
            TR.words__error,
            "{}",
            description_param=_describe(exception),
            timeout_ms=_ERROR_POPUP_TIMEOUT_MS,
        ) as popup:
            await interact_simple(popup)
    except Exception as e:
        # never let the screen hide the app's real failure
        if __debug__:
            log.error(__name__, f"Failed to show error screen: {_describe(e)}")


async def _serve(session: Session, request: ExtAppMessage) -> ExtAppResponse:
    try:
        session.send(SERVICE_WIRE_START, request.message_id, request.data)
    except Exception as e:
        session.die(
            DataError(
                f"Failed to send request {request.message_id} to app: {_describe(e)}"
            )
        )

    # last service the app called, to tell where it stopped
    last_service = SERVICE_WIRE_START
    while True:
        if not session.image.is_running():
            session.dead = True
            raise DataError(
                f"App {request.instance_id} stopped after service {last_service}"
            )
        try:
            msg: IpcMessage = await loop.wait(
                io.IPC2_EVENT | io.POLL_READ, timeout_ms=_IPC_TIMEOUT_MS
            )
        except loop.Timeout:
            # Core is not woken when the app is killed (e.g. by the watchdog),
            # so report a dead app as stopped rather than as a timeout.
            if not session.image.is_running():
                session.dead = True
                raise DataError(
                    f"App {request.instance_id} stopped after service {last_service}"
                )
            session.die(
                DataError(
                    f"No message from app within {_IPC_TIMEOUT_MS} ms after service {last_service}"
                )
            )

        service = msg.service
        last_service = service
        try:
            if service == SERVICE_WIRE_END:
                return wire.end(msg)
            elif service == SERVICE_WIRE_CONTINUE:
                await wire.handle_continue(session, msg)
            elif service == SERVICE_WIRE_ERROR:
                await wire.handle_error(session, msg)
            elif service == SERVICE_UI:
                await ui.handle(session, msg)
            elif service == SERVICE_PROGRESS:
                progress.handle(session, msg)
            elif service == SERVICE_CRYPTO:
                await crypto.handle(session, msg)
            else:
                session.die(
                    DataError(
                        f"Unknown IPC service {service} (message {msg.message_id})"
                    )
                )
        except (
            Error,
            MemoryError,
            loop.TaskClosed,
            ui_shutdown,
            context.UnexpectedMessageException,
        ):
            # failures with their own code and message, and workflow control flow
            raise
        except Exception as e:
            # a bare exception would reach the host as an empty `FirmwareError`;
            # stop the app too, it may still be waiting for Core's answer
            session.die(
                FirmwareError(
                    f"Service {service} (message {msg.message_id}) failed: {e.__class__.__name__}: {e}"
                )
            )


def _open_session(request: ExtAppMessage) -> Session:
    """Check that `request` targets the app launched in this session and that
    it is still running."""
    if request.message_id > 0xFFFF:
        raise DataError(f"Invalid message ID: {request.message_id}")

    instance_ids = context.cache_get(cc.APP_EXTAPP_IDS)
    if instance_ids is None:
        raise DataError(f"No app running for instance ID: {request.instance_id}")
    image_handle, instance_id = ustruct.unpack("<II", instance_ids)
    if instance_id != request.instance_id:
        raise DataError(
            f"Invalid instance ID: {request.instance_id} (running: {instance_id})"
        )

    image = app.image_by_handle(image_handle)

    curves: list[str] = list(image.allowed_curves())
    if len(curves) != 1:
        raise DataError(f"Expected exactly one allowed curve, got {curves}")
    patterns: list[str] = list(image.allowed_paths())
    if __debug__:
        log.debug(__name__, f"Allowed curves: {curves}, patterns: {patterns}")
    schemas = [paths.PathSchema.parse(p, _SLIP44_ID) for p in patterns]
    # allocate the schemas in a contiguous block of memory
    schemas = [s.copy() for s in schemas]

    if not image.is_running():
        raise DataError(f"Task not running: {request.instance_id}")

    return Session(image, curves[0], schemas)
