from typing import TYPE_CHECKING

import ustruct

from storage import cache_common as cc
from storage.cache import get_sessionless_cache

from trezor import app
from trezor.crypto import random
from trezor.wire import context

from trezor.messages import ExtAppLoad, ExtAppLoaded, DataChunkRequest, DataChunkAck
from trezor.wire.errors import DataError

if TYPE_CHECKING:
    from buffer_types import AnyBytes


async def _load_image(hash: AnyBytes, size: int) -> None:
    image = app.create_image(hash, size)
    offset = 0
    while offset < size:
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
        image.write(offset, chunk)
        offset += len(chunk)
    image.finalize(True)


async def load(msg: ExtAppLoad) -> ExtAppLoaded:
    from trezor import app

    """Load external application from a host and return its hash."""
    try:
        task = app.spawn_task(msg.hash)
    except RuntimeError as e:
        pass

    try:
        await _load_image(msg.hash, msg.size)
    except Exception as e:
        raise DataError(f"ExtApp load failed: {e}") from e
    else:
        task = app.spawn_task(msg.hash)

    instance_id = random.uniform(2**32 - 1)
    cache_entry = ustruct.pack("<BI", task.id(), instance_id)
    get_sessionless_cache().set(cc.APP_EXTAPP_IDS, cache_entry)
    return ExtAppLoaded(instance_id=instance_id)
