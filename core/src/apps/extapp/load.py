from typing import TYPE_CHECKING

import storage.device as storage_device
import ustruct  # pyright: ignore[reportMissingImports]
from storage import cache_common as cc
from storage.cache import get_sessionless_cache
from trezor import log
from trezor.crypto import random
from trezor.messages import (
    ExtAppDataChunkAck,
    ExtAppDataChunkRequest,
    ExtAppHeaderAck,
    ExtAppHeaderRequest,
    ExtAppLoad,
    ExtAppLoaded,
    ExtAppRootPacketAck,
    ExtAppRootPacketRequest,
    Version,
)
from trezor.wire import context
from trezor.wire.errors import DataError
from trezordefinitions import app_root_min_timestamp

if TYPE_CHECKING:
    from trezor import app


def image_matches(image: app.AppImage, msg: ExtAppLoad) -> bool:
    v = msg.version
    if image.id() != msg.id:
        return False
    if image.version() < (v.major, v.minor, v.patch, v.build):
        return False
    if msg.fingerprint != b"" and image.fingerprint() != msg.fingerprint:
        return False
    return True


async def _load_image(msg: ExtAppLoad) -> app.AppImage:
    from trezor import app
    from trezor.ui.layouts.progress import progress

    # ---------------------------------------------------------------
    # Request app header
    # ---------------------------------------------------------------

    header_ack = await context.call(
        ExtAppHeaderRequest(),
        ExtAppHeaderAck,
    )

    # ---------------------------------------------------------------
    # Check whether the root packet is already loaded and up to date.
    # ---------------------------------------------------------------

    app_ring = app.app_ring_from_header(header_ack.header)

    if app.root_is_loaded(app_ring):
        root_timestamp = app.root_timestamp(app_ring)
    else:
        root_timestamp = 0

    if root_timestamp != header_ack.root_packet_timestamp:
        root_packet_ack = await context.call(
            ExtAppRootPacketRequest(app_ring=app_ring),
            ExtAppRootPacketAck,
        )

        # Update the root packet
        min_timestamp = app_root_min_timestamp()
        state = app.AppRootState(min_timestamp, storage_device.get_app_root_state())
        app.root_update(root_packet_ack.root_packet, state)
        storage_device.set_app_root_state(state.serialize())

    # ---------------------------------------------------------------
    # Create image and load chunks
    # ---------------------------------------------------------------

    image = app.create_image(header_ack.header, header_ack.proof)

    if not image_matches(image, msg):
        image.delete()
        raise DataError("Loaded image does not match the expected app")

    prog = progress("Loading app...")
    chunk_size = image.chunk_size()
    chunk_count = (image.size() + chunk_size - 1) // chunk_size
    for chunk_index in range(chunk_count):
        prog.report(int(chunk_index / chunk_count * 1000))
        chunk = await context.call(
            ExtAppDataChunkRequest(
                index=chunk_index,
            ),
            ExtAppDataChunkAck,
        )
        image.write_chunk(chunk.data, chunk.hash)

    if not image.is_ready():
        image.delete()
        # Image was not fully loaded, probably truncated by the host.
        raise DataError("App image truncated")

    prog.stop()
    return image


async def load(msg: ExtAppLoad) -> ExtAppLoaded:
    """Load external application from a host"""
    from trezor import app

    try:
        image = next(app.images())
    except StopIteration:
        image = None

    if image is not None:
        if not image_matches(image, msg) or not image.is_ready():
            image.delete()
            image = None
        elif image.is_running():
            image.stop()  # ensure clean state

    if image is None:
        try:
            image = await _load_image(msg)
        except app.AppImageVerificationError as e:
            log.exception(__name__, e)
            raise DataError("App image verification failed")
        except app.AppImageMemoryError as e:
            log.exception(__name__, e)
            raise DataError("Not enough memory to load app")
        except app.AppError as e:
            log.exception(__name__, e)
            raise DataError("Failed to load app")

    image.run()

    instance_id = random.uniform(2**32 - 1)
    cache_entry = ustruct.pack("<II", image.handle(), instance_id)
    get_sessionless_cache().set(cc.APP_EXTAPP_IDS, cache_entry)
    major, minor, patch, build = image.version()
    return ExtAppLoaded(
        instance_id=instance_id,
        version=Version(major=major, minor=minor, patch=patch, build=build),
    )
