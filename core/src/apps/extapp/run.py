from micropython import const
from typing import TYPE_CHECKING

import ustruct  # pyright: ignore[reportMissingImports]
from storage import cache_common as cc
from trezor import TR, app, io, loop
from trezor.enums import MessageType
from trezor.messages import ExtAppMessage
from trezor.ui import Shutdown as ui_shutdown
from trezor.ui.layouts import error_popup, interact_simple
from trezor.wire import context
from trezor.wire.errors import DataError, Error, ProcessError

from apps.common import paths, safety_checks

from . import crypto, progress, ui, wire
from .session import (
    LIFECYCLE_ABORT,
    SERVICE_CRYPTO,
    SERVICE_LIFECYCLE,
    SERVICE_PROGRESS,
    SERVICE_UI,
    SERVICE_WIRE,
    SERVICE_WIRE_ERROR,
    Session,
    describe,
)

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from trezorio import IpcMessage
    from typing import Any

    from trezor.messages import ExtAppResponse

# The apps' allowed path patterns hardcode their coin type, so the SLIP-44 ID
# only fills unused placeholders; 1 is the testnet ID.
_SLIP44_ID = const(1)

# how long the error screen stays up before the app's failure is reported
_ERROR_POPUP_TIMEOUT_MS = const(2000)

# how long Core waits for the app's next IPC message
_IPC_TIMEOUT_MS = const(20000)

# how long a stopped app has to exit on its own
_STOP_TIMEOUT_MS = const(250)

# an app registers its inbox once it runs, Core retries until then
_START_RETRY_MS = const(1)
_START_RETRIES = const(1000)

_IPC_EVENT = io.IPC2_EVENT | io.POLL_READ
_APP_EXIT_EVENT = io.APP_ARENA_EVENT | io.POLL_READ


async def run(request: ExtAppMessage) -> ExtAppResponse | None:
    """Restart the app, forward `request` to it and serve it until it exits or
    has to stop. Returns the final response of an app that exited after sending
    it, the other responses go straight to the host."""
    session = await _start_app(request)
    response = None
    try:
        try:
            response = await _serve(session, request)
        except (GeneratorExit, loop.TaskClosed):
            # a closed workflow can't wait for the app anymore
            session.stop()
            raise
        finally:
            try:
                await _stop_app(session)
            finally:
                # the app is gone, its unread messages would outlive it
                _ipc_cleanup()
        if not session.response_sent:
            session.die("App exited without a response")
        return response
    except Exception as e:
        if session.dead:
            await _show_error(session, e)
        raise


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
            description_param=describe(exception),
            timeout_ms=_ERROR_POPUP_TIMEOUT_MS,
        ) as popup:
            await interact_simple(popup)
    except Exception as e:
        # never let the screen hide the app's real failure
        if __debug__:
            log.error(__name__, f"Failed to show error screen: {describe(e)}")


async def _start_app(request: ExtAppMessage) -> Session:
    """Check that `request` targets the loaded app, then start it anew."""
    if request.message_id > 0xFFFF:
        raise DataError("Invalid message ID")

    instance_ids = context.cache_get(cc.APP_EXTAPP_IDS)
    if instance_ids is None:
        raise DataError("Invalid instance ID")
    image_handle, instance_id = ustruct.unpack("<II", instance_ids)
    if instance_id != request.instance_id:
        raise DataError("Invalid instance ID")

    # apps can't see the level, so they only run with strict checks; the level
    # can't change while an app runs
    if not safety_checks.is_strict():
        raise ProcessError("Safety checks must be strict")

    image = app.image_by_handle(image_handle)
    image.stop()
    _ipc_cleanup()

    curves: list[str] = list(image.allowed_curves())
    patterns: list[str] = list(image.allowed_paths())
    if __debug__:
        log.debug(__name__, f"Allowed curves: {curves}, patterns: {patterns}")
    schemas = [paths.PathSchema.parse(p, _SLIP44_ID) for p in patterns]
    # allocate the schemas in a contiguous block of memory
    schemas = [s.copy() for s in schemas]

    image.run()
    return Session(image, instance_id, curves, schemas)


async def _poll_message() -> IpcMessage | None:
    """A message already queued from the app, or `None`; does not block."""
    try:
        return await loop.wait(_IPC_EVENT, timeout_ms=0)
    except loop.Timeout:
        return None


def _ipc_cleanup() -> None:
    """Core's queue outlives the app, so a killed app can leave messages in it.
    Doesn't block or await, so it also works in a closed workflow."""
    msg_entry: list[Any] = [0, 0]
    while io.poll((_IPC_EVENT,), msg_entry, 0):
        pass


async def _stop_app(session: Session) -> None:
    """Have the app exit on its own, or kill it. The app must be gone once
    this returns."""
    if session.stopped:
        return

    image = session.image
    if image.is_running():
        try:
            session.send(SERVICE_LIFECYCLE, LIFECYCLE_ABORT, b"")
        except Exception:
            pass  # the timeout below takes care of it
        while image.is_running():
            try:
                await loop.wait(_APP_EXIT_EVENT, timeout_ms=_STOP_TIMEOUT_MS)
            except loop.Timeout:
                session.die("App did not stop")

    if not image.exited_normally():
        session.die("App crashed")


async def _send_request(session: Session, request: ExtAppMessage) -> None:
    retries = _START_RETRIES
    while True:
        try:
            session.send(SERVICE_WIRE, request.message_id, request.data)
            return
        except Exception as e:
            retries -= 1
            if retries == 0 or not session.image.is_running():
                session.die(
                    f"Failed to send request {request.message_id}: {describe(e)}"
                )
        await loop.sleep(_START_RETRY_MS)


async def _next_message(session: Session) -> IpcMessage | None:
    """Next message from the app, or `None` once the app has exited and
    everything it sent is handled. The host's messages are passed to the app."""
    while True:
        if not session.image.is_running():
            # the app's last messages outlive it
            return await _poll_message()

        msg: Any
        app_exit = loop.wait(_APP_EXIT_EVENT)
        if session.response_sent:
            # the app has answered, it's up to the host now
            host = context.get_context().read(
                (MessageType.ExtAppMessage,), ExtAppMessage
            )
            msg = await loop.race(loop.wait(_IPC_EVENT), app_exit, host)
        else:
            app_message = loop.wait(_IPC_EVENT, timeout_ms=_IPC_TIMEOUT_MS)
            msg = await loop.race(app_message, app_exit)

        if msg is None:
            continue
        if not ExtAppMessage.is_type_of(msg):
            return msg
        wire.handle_host_message(session, msg)


async def _serve(session: Session, request: ExtAppMessage) -> ExtAppResponse | None:
    await _send_request(session, request)

    # last service the app called, to tell where it stopped
    last_service = SERVICE_WIRE
    while True:
        try:
            msg = await _next_message(session)
        except loop.Timeout:
            session.die(
                f"No message from app within {_IPC_TIMEOUT_MS} ms after service {last_service}"
            )

        if msg is None:
            return None

        service = msg.service
        last_service = service
        try:
            if service == SERVICE_WIRE:
                if not session.image.is_running():
                    # like any workflow result, the app's last message is sent
                    # once the workflow has ended and the homescreen is back
                    return wire.final_response(session, msg)
                await wire.handle(session, msg)
            elif service == SERVICE_WIRE_ERROR:
                wire.handle_error(session, msg)
            elif service == SERVICE_UI:
                await ui.handle(session, msg)
            elif service == SERVICE_PROGRESS:
                progress.handle(session, msg)
            elif service == SERVICE_CRYPTO:
                await crypto.handle(session, msg)
            else:
                session.die(f"Unknown IPC service {service} (message {msg.message_id})")
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
            # stop the app, it may still be waiting for Core's answer
            session.die(
                f"Service {service} (message {msg.message_id}) failed: {e.__class__.__name__}: {e}"
            )
