import ustruct
from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from buffer_types import AnyBytes


async def _load_image(hash: AnyBytes, size: int) -> app.AppImage:
    from trezor.ui.layouts.progress import progress

    image = app.create_image()
    offset = 0
    prog = progress("Loading app...")
    while offset < size:
        prog.report(int(offset / size * 1000))
        chunk = (
            await context.call(
                DataChunkRequest(
                    data_length=min(size - offset, 1024), data_offset=offset
                ),
                DataChunkAck,
            )
        ).data_chunk
        if len(chunk) != min(size - offset, 1024):
            raise DataError("Data length mismatch")
        image.write_chunk(chunk)
        offset += len(chunk)
    image.verify(b"")  # !@# TODO use real proof
    prog.stop()
    return image


async def load(msg: TrezorAppLoad) -> TrezorAppLoaded:
    """Load external application from a host and return its hash."""
    from trezor import app

    image = app.get_image_by_index(0)

    if image is not None:
        version = (msg.version[0] << 24) | (msg.version[1] << 16)
        
        info = image.get_info()

        id_ok = msg.id == info.identifier
        version_ok = version >= info.version
        hash_ok = msg.hash == b'' #or image.hash == msg.hash TODO

        if not (version_ok and id_ok and hash_ok):
            image.delete()
            image = None

    if image is None:
        try:
            image = await _load_image(msg.hash, msg.size)
            assert image is not None
        except Exception as e:
            raise DataError(f"TrezorApp load failed: {e}") from e

    image.run()

    instance_id = random.uniform(2**32 - 1)
    cache_entry = ustruct.pack("<BI", image.get_handle(), instance_id)
    get_sessionless_cache().set(cc.APP_EXTAPP_IDS, cache_entry)
    return TrezorAppLoaded(instance_id=instance_id)
