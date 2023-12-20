from micropython import const
from typing import TYPE_CHECKING

from trezor import messages, protobuf
from trezor.wire import ProcessError
from trezor.wire.context import call as ctx_call

if TYPE_CHECKING:
    from typing import Generic, TypeVar, Union

    Chunk = Union[
        messages.CardanoTxInlineDatumChunk,
        messages.CardanoTxReferenceScriptChunk,
        messages.CardanoMessagePayloadChunk,
    ]

    C = TypeVar("C", bound=Chunk)
else:
    # typechecker cheat
    Generic = (object,)
    C = Chunk = 0

MAX_CHUNK_SIZE = const(1024)


def _get_chunks_count(size: int) -> int:
    """Integer-only version of `ceil(size / MAX_CHUNK_SIZE)`."""
    assert size >= 0
    return (size + MAX_CHUNK_SIZE - 1) // MAX_CHUNK_SIZE


def _validate_chunk(
    chunk: Chunk,
    chunk_index: int,
    total_size: int,
) -> None:
    chunks_count = _get_chunks_count(total_size)
    assert chunk_index < chunks_count

    if len(chunk.data) > MAX_CHUNK_SIZE:
        raise ProcessError("Invalid chunk: Too large")

    is_last_chunk = chunk_index == chunks_count - 1

    if not is_last_chunk and len(chunk.data) < MAX_CHUNK_SIZE:
        raise ProcessError("Invalid intermediate chunk: Too small")

    if (
        is_last_chunk
        # check whether this chunk and preceding chunks add up to the supposed size
        and len(chunk.data) + MAX_CHUNK_SIZE * (chunks_count - 1) != total_size
    ):
        raise ProcessError("Invalid last chunk: Size inconsistent with total bytes")


class ChunkIterator(Generic[C]):
    def __init__(
        self,
        total_size: int,
        ack_msg: protobuf.MessageType,
        chunk_type: type[C],
    ) -> None:
        self.ack_msg = ack_msg
        self.chunk_type = chunk_type
        self.chunk_index = 0
        self.chunks_count = _get_chunks_count(total_size)
        self.total_size = total_size

    def __aiter__(self) -> "ChunkIterator":
        return self

    async def __anext__(self) -> tuple[int, C]:
        if self.chunk_index >= self.chunks_count:
            raise StopAsyncIteration
        chunk: C = await ctx_call(self.ack_msg, self.chunk_type)
        _validate_chunk(chunk, chunk_index=self.chunk_index, total_size=self.total_size)
        result = (self.chunk_index, chunk)
        self.chunk_index += 1
        return result
