from typing import TYPE_CHECKING, Awaitable, Container

from storage import cache_codec
from storage.cache_common import DataCache, InvalidSessionError
from trezor import log, protobuf
from trezor.wire.codec import codec_v1
from trezor.wire.context import UnexpectedMessageException
from trezor.wire.protocol_common import Context, Message

if TYPE_CHECKING:
    from typing import TypeVar

    from trezor.wire import WireInterface

    LoadedMessageType = TypeVar("LoadedMessageType", bound=protobuf.MessageType)


class CodecContext(Context):
    """ "Wire context" for `protocol_v1`."""

    def __init__(
        self,
        iface: WireInterface,
        buffer: bytearray,
    ) -> None:
        self.buffer = buffer
        super().__init__(iface)

    def read_from_wire(self) -> Awaitable[Message]:
        """Read a whole message from the wire without parsing it."""
        return codec_v1.read_message(self.iface, self.buffer)

    async def read(
        self,
        expected_types: Container[int],
        expected_type: type[protobuf.MessageType] | None = None,
    ) -> protobuf.MessageType:
        if __debug__:
            log.debug(
                __name__,
                "%d: expect: %s",
                self.iface.iface_num(),
                expected_type.MESSAGE_NAME if expected_type else expected_types,
            )

        # Load the full message into a buffer, parse out type and data payload
        msg = await self.read_from_wire()

        # If we got a message with unexpected type, raise the message via
        # `UnexpectedMessageError` and let the session handler deal with it.
        if msg.type not in expected_types:
            raise UnexpectedMessageException(msg)

        if expected_type is None:
            expected_type = protobuf.type_for_wire(msg.type)

        if __debug__:
            log.debug(
                __name__,
                "%d: read: %s",
                self.iface.iface_num(),
                expected_type.MESSAGE_NAME,
            )

        # look up the protobuf class and parse the message
        from ..message_handler import wrap_protobuf_load

        return wrap_protobuf_load(msg.data, expected_type)

    async def write(self, msg: protobuf.MessageType) -> None:
        if __debug__:
            log.debug(
                __name__,
                "%d: write: %s",
                self.iface.iface_num(),
                msg.MESSAGE_NAME,
            )

        # cannot write message without wire type
        assert msg.MESSAGE_WIRE_TYPE is not None

        msg_size = protobuf.encoded_length(msg)

        if msg_size <= len(self.buffer):
            # reuse preallocated
            buffer = self.buffer
        else:
            # message is too big, we need to allocate a new buffer
            buffer = bytearray(msg_size)

        msg_size = protobuf.encode(buffer, msg)
        await codec_v1.write_message(
            self.iface,
            msg.MESSAGE_WIRE_TYPE,
            memoryview(buffer)[:msg_size],
        )

    def release(self) -> None:
        cache_codec.end_current_session()

    # ACCESS TO CACHE
    @property
    def cache(self) -> DataCache:
        c = cache_codec.get_active_session()
        if c is None:
            raise InvalidSessionError()
        return c
