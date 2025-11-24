from micropython import const
from typing import TYPE_CHECKING

from trezor.messages import DataChunkAck, DataChunkRequest
from trezor.wire import DataError
from trezor.wire.context import call, get_context

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from typing import Callable

_CHUNK_SIZE = const(1024)


async def get_data_chunk(data_left: int, offset: int) -> AnyBytes:
    data_length = min(data_left, _CHUNK_SIZE)
    req = DataChunkRequest(data_length=data_length, data_offset=offset)
    res = await call(req, DataChunkAck)
    if len(res.data_chunk) != data_length:
        raise DataError("Data length mismatch")
    return res.data_chunk


async def get_all_chunks(
    buffer: bytearray,
    length: int,
    offset: int = 0,
    report: Callable[[int], None] | None = None,
) -> None:
    with get_context().high_speed():
        data_left = length
        # Requesting the data in chunks and storing them in the blob
        while data_left > 0:
            data_chunk = await get_data_chunk(data_left, offset)
            buffer.extend(data_chunk)
            data_left -= len(data_chunk)
            offset += len(data_chunk)
            if report is not None:
                report((length - data_left) * 1000 // length)
