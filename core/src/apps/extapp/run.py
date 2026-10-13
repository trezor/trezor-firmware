from micropython import const
from typing import TYPE_CHECKING

import ustruct  # pyright: ignore[reportMissingImports]
from storage import cache_common as cc
from trezor import app, io, loop
from trezor.wire import context
from trezor.wire.errors import DataError

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


async def run(request: ExtAppMessage) -> ExtAppResponse:
    """Forward `request` to the running app and serve its IPC requests until
    it sends its final response."""
    session = _open_session(request)

    try:
        session.send(SERVICE_WIRE_START, request.message_id, request.data)
    except Exception as e:
        session.die(DataError(f"Failed to send IPC message: {e}"))

    while True:
        if not session.image.is_running():
            raise DataError(f"Task stopped: {request.instance_id}")
        try:
            msg: IpcMessage = await loop.wait(
                io.IPC2_EVENT | io.POLL_READ, timeout_ms=1000
            )
        except loop.Timeout:
            session.die(DataError("Timeout waiting for message"))

        service = msg.service
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
            if __debug__:
                log.error(
                    __name__,
                    f"Unknown IPC function: service={service}, message_id={msg.message_id}",
                )
            session.die(RuntimeError("Unknown IPC function"))


def _open_session(request: ExtAppMessage) -> Session:
    """Check that `request` targets the app launched in this session and that
    it is still running."""
    if request.message_id > 0xFFFF:
        raise DataError("Invalid message ID.")

    instance_ids = context.cache_get(cc.APP_EXTAPP_IDS)
    if instance_ids is None:
        raise DataError(f"Invalid instance ID: {request.instance_id}")
    image_handle, instance_id = ustruct.unpack("<II", instance_ids)
    if instance_id != request.instance_id:
        raise DataError(f"Invalid instance ID: {request.instance_id}")

    image = app.image_by_handle(image_handle)

    curves: list[str] = list(image.allowed_curves())
    if len(curves) != 1:
        raise DataError("Expected exactly one allowed curve")
    patterns: list[str] = list(image.allowed_paths())
    if __debug__:
        log.debug(__name__, f"Allowed curves: {curves}, patterns: {patterns}")
    schemas = [paths.PathSchema.parse(p, _SLIP44_ID) for p in patterns]
    # allocate the schemas in a contiguous block of memory
    schemas = [s.copy() for s in schemas]

    if not image.is_running():
        raise DataError(f"Task not running: {request.instance_id}")

    return Session(image, curves[0], schemas)
