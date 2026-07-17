import ustruct

from storage import cache_common as cc
from storage.cache import get_sessionless_cache
from trezor import app, log
from trezor.crypto import random
from trezor.messages import (
    TrezorAppDataChunkAck,
    TrezorAppDataChunkRequest,
    TrezorAppHeaderAck,
    TrezorAppHeaderRequest,
    TrezorAppLoad,
    TrezorAppLoaded,
    TrezorAppRootPacketAck,
    TrezorAppRootPacketRequest,
)
from trezor.wire import context
from trezor.wire.errors import DataError


def image_matches(image: app.AppImage, msg: TrezorAppLoad) -> bool:
    if image.id() != msg.id:
        return False
    if image.version() < tuple(msg.version):
        return False
    if msg.hash != b"" and image.header_hash() != msg.hash:
        return False
    return True


async def _load_image(msg: TrezorAppLoad) -> app.AppImage:
    from trezor import app
    from trezor.ui.layouts.progress import progress

    # ---------------------------------------------------------------
    # Request app header
    # ---------------------------------------------------------------

    header_ack = await context.call(
        TrezorAppHeaderRequest(),
        TrezorAppHeaderAck,
    )

    # ---------------------------------------------------------------
    # Check whether the root packet is already loaded and up to date.
    # ---------------------------------------------------------------

    app_ring = app.app_ring_from_header(header_ack.header)

    if app.root_is_loaded(app_ring):
        root_timestamp = app.root_timestamp(app_ring)
    else:
        root_timestamp = 0

    if root_timestamp != header_ack.timestamp:
        root_packet_ack = await context.call(
            TrezorAppRootPacketRequest(
                app_ring=app_ring,
                host_timestamp_stale=root_timestamp > header_ack.timestamp,
            ),
            TrezorAppRootPacketAck,
        )

        app.root_update(root_packet_ack.root_packet)

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
            TrezorAppDataChunkRequest(
                index=chunk_index,
            ),
            TrezorAppDataChunkAck,
        )
        image.write_chunk(chunk.data, chunk.hash)

    if not image.is_ready():
        image.delete()
        # Image was not fully loaded, probably truncated by the host.
        raise DataError("App image truncated")

    prog.stop()
    return image


async def load(msg: TrezorAppLoad) -> TrezorAppLoaded:
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
    return TrezorAppLoaded(instance_id=instance_id)
