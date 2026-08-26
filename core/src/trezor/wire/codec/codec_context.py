from typing import TYPE_CHECKING, Awaitable, Container

from trezor import protobuf, utils
from trezor.wire.codec import codec_v1
from trezor.wire.context import UnexpectedMessageException
from trezor.wire.message_handler import decode_message
from trezor.wire.protocol_common import Context, Message

if __debug__:
    from trezor import log


if TYPE_CHECKING:
    from typing import TypeVar

    from buffer_types import AnyBuffer

    from storage.cache_common import DataCache

    from .. import WireInterface
    from .buffers import CodecBufferSource

    LoadedMessageType = TypeVar("LoadedMessageType", bound=protobuf.MessageType)


class CodecContext(Context):
    """ "Wire context" for `protocol_v1`."""

    def __init__(
        self,
        iface: WireInterface,
        buffers: CodecBufferSource,
    ) -> None:
        self.buffers = buffers
        super().__init__(iface)

    def read_from_wire(self) -> Awaitable[Message]:
        """Read a whole message from the wire without parsing it.

        The returned `Message` carries the receive lease; whoever decodes it ends it. See
        `message_handler.decode_message`.
        """
        return codec_v1.read_message(self.iface, self.buffers)

    async def read(
        self,
        expected_types: Container[int] | None,
        expected_type: type[protobuf.MessageType] | None = None,
    ) -> protobuf.MessageType:
        if __debug__:
            log.debug(
                __name__,
                "expect: %s",
                expected_type.MESSAGE_NAME if expected_type else expected_types,
                iface=self.iface,
            )

        # Load the full message into a buffer, parse out type and data payload
        msg = await self.read_from_wire()

        # If we got a message with unexpected type, raise the message via
        # `UnexpectedMessageError` and let the session handler deal with it.
        if not expected_types or msg.type not in expected_types:
            raise UnexpectedMessageException(msg)

        if expected_type is None:
            expected_type = protobuf.type_for_wire(
                self.message_type_enum_name, msg.type
            )

        if __debug__:
            log.debug(
                __name__,
                "read: %s",
                expected_type.MESSAGE_NAME,
                iface=self.iface,
            )

        # look up the protobuf class and parse the message, ending the receive lease
        return decode_message(msg, expected_type)

    async def write(self, msg: protobuf.MessageType) -> None:
        if __debug__:
            log.debug(
                __name__,
                "write: %s",
                msg.MESSAGE_NAME,
                iface=self.iface,
            )

        # cannot write message without wire type
        assert msg.MESSAGE_WIRE_TYPE is not None

        msg_size = protobuf.encoded_length(msg)

        # A READ STILL IN FLIGHT KEEPS ITS LEASE, AND ITS MEMORY. `read` raises
        # `UnexpectedMessageException` with the message undecoded, and the workflow loop then
        # writes a response before that message is handled -- so a write that took the lease and
        # gave it back would hand the shared buffer away while a `Message` still views into it.
        #
        # NOT ENOUGH TO KEEP THE LEASE, which is what this used to do. `SharedBuffer.acquire`
        # returns True for the holder that already owns it, so `get()` would hand back the very
        # bytes the pending `Message.data` points at and the response would be encoded over the
        # request. Skip the pool entirely instead: what is written from under a held read lease is
        # a `Failure` or a short answer, so the heap costs nothing.
        held_for_a_read = self.buffers.holds_shared()

        buffer: AnyBuffer | None = None
        if not held_for_a_read and msg_size <= self.buffers.capacity():
            buffer = self.buffers.get(msg_size)
        leased = buffer is not None

        if buffer is None:
            if not held_for_a_read and 128 < msg_size <= self.buffers.capacity():
                # The shared buffer is held by another message in flight. Small responses are
                # still allowed through on the heap, which is what lets a `Failure` explaining
                # exactly that reach the host. Not reachable when WE are the holder -- that is
                # not contention, and the heap below is the answer rather than a refusal.
                raise IOError
            # Too large for the pool, a small response while the pool is busy, or a response
            # written while this connection's own read still views the shared buffer.
            buffer = bytearray(msg_size)

        try:
            msg_size = protobuf.encode(buffer, msg)
            await codec_v1.write_message(
                self.iface,
                msg.MESSAGE_WIRE_TYPE,
                memoryview(buffer)[:msg_size],
            )
        finally:
            # THE SEND LEASE ENDS HERE, and it has to end even on a failed write: the message is
            # gone either way, and a lease outliving it would strand the buffer for good.
            if leased:
                self.buffers.release()

    if not utils.USE_THP:
        # Note: we use the above CodecContext functionality for DebugLink on PYOPT=0 builds.
        # The methods below are excluded for THP builds, since cache_codec is not available.

        def release(self) -> None:
            from storage.cache_codec import end_current_session

            end_current_session()

        # ACCESS TO CACHE
        @property
        def cache(self) -> DataCache:
            from storage.cache_codec import get_active_session
            from storage.cache_common import InvalidSessionError

            c = get_active_session()
            if c is None:
                raise InvalidSessionError()
            return c
