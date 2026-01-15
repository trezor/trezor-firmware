import ustruct

from storage import cache_common as cc
from storage.cache import get_sessionless_cache
from trezor import app
from trezor.crypto import random
from trezor.messages import (
    DataChunkAck,
    DataChunkRequest,
    TrezorAppLoad,
    TrezorAppLoaded,
)
from trezor.wire import context
from trezor.wire.errors import DataError


def image_matches(image: app.AppImage, msg: TrezorAppLoad) -> bool:
    if not image.is_verified():
        return False
    if image.get_id() != msg.id:
        return False
    if image.get_version() < tuple(msg.version):
        return False
    if msg.hash != b"" and image.get_hash() != msg.hash:
        return False
    return True


async def _load_image(msg: TrezorAppLoad) -> app.AppImage:
    from trezor import app
    from trezor.ui.layouts.progress import progress

    image = app.create_image()
    offset = 0
    prog = progress("Loading app...")
    while offset < msg.size:
        prog.report(int(offset / msg.size * 1000))
        chunk = (
            await context.call(
                DataChunkRequest(
                    data_length=min(msg.size - offset, 1024), data_offset=offset
                ),
                DataChunkAck,
            )
        ).data_chunk
        if len(chunk) != min(msg.size - offset, 1024):
            raise DataError("Data length mismatch")
        image.write_chunk(chunk)
        offset += len(chunk)
    image.verify(b"")  # !@# TODO use real proof
    if not image_matches(image, msg):
        image.delete()
        raise DataError("Loaded image does not match the expected app")
    prog.stop()
    return image


async def load(msg: TrezorAppLoad) -> TrezorAppLoaded:
    """Load external application from a host and return its hash."""
    from trezor import app

    image = app.get_image_by_index(0)

    if image is not None:
        if not image_matches(image, msg):
            image.delete()
            image = None
        elif image.is_running():
            image.stop()  # ensure clean state

    if image is None:
        try:
            image = await _load_image(msg)
            assert image is not None
        except Exception as e:
            raise DataError(f"Failed to load app: {e}") from e

    image.run()

    instance_id = random.uniform(2**32 - 1)
    cache_entry = ustruct.pack("<BI", image.get_handle(), instance_id)
    get_sessionless_cache().set(cc.APP_EXTAPP_IDS, cache_entry)
    return TrezorAppLoaded(instance_id=instance_id)
