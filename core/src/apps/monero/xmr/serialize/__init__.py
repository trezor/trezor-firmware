from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import TypeVar

    from .message_types import MessageType

    T = TypeVar("T", bound=MessageType)


def parse_msg(buf: bytes, msg_type: type[T]) -> T:
    from apps.monero.xmr.serialize.readwriter import MemoryReaderWriter

    reader = MemoryReaderWriter(memoryview(buf))
    return msg_type.load(reader)


def dump_msg(
    msg: MessageType, preallocate: int | None = None, prefix: bytes | None = None
) -> bytes:
    from apps.monero.xmr.serialize.readwriter import MemoryReaderWriter

    writer = MemoryReaderWriter(preallocate=preallocate)
    if prefix:
        writer.write(prefix)
    msg_type = msg.__class__
    msg_type.dump(writer, msg)

    return writer.get_buffer()
