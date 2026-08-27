# flake8: noqa: F403,F405
from common import *  # isort:skip

from mock_wire_interface import MockHID
from trezor import io, protobuf, utils
from trezor.enums import MessageType
from trezor.messages import Failure
from trezor.wire import message_handler
from trezor.wire.buffers import SharedBuffer, WireBuffer
from trezor.wire.errors import DataError
from trezor.wire.protocol_common import Message

if not utils.USE_THP:
    from trezor.wire.codec.buffers import CodecBufferSource
    from trezor.wire.codec.codec_context import CodecContext

UNREGISTERED_WIRE_TYPE = 0xFEFE


def _run(coro):
    """Drive a coroutine whose only awaits complete immediately."""
    try:
        while True:
            coro.send(None)
    except StopIteration as e:
        return e.value


class _RecordingContext:
    """Just enough `Context` for `handle_single_message`, and nothing that hides a lease."""

    message_type_enum_name = "MessageType"

    def __init__(self):
        self.iface = MockHID()
        self.channel_id = 0
        self.written = []

    async def write(self, msg):
        self.written.append(msg)


@unittest.skipUnless(not utils.USE_THP, "the codec buffer source exists only in a codec build")
class TestHandleSingleMessageLease(unittest.TestCase):
    """Every exit that does not reach `decode_message` has to end the receive lease itself.

    THE BUFFER IS SHARED ACROSS INTERFACES, which is what makes this more than untidy: a lease
    stranded by one malformed request on one interface is a large-message denial of service on
    the other, for the rest of the session.
    """

    def setUp(self):
        self.shared = SharedBuffer(1024)
        self.source = CodecBufferSource(WireBuffer(0), self.shared)
        self._filters = message_handler.filters[:]

    def tearDown(self):
        message_handler.filters[:] = self._filters

    def _leased_message(self, msg_type):
        buffer = self.source.get(64)
        self.assertIsNotNone(buffer)
        self.assertTrue(self.source.holds_shared())
        return Message(msg_type, buffer, self.source)

    def test_an_unregistered_wire_type_leaves_no_lease(self):
        ctx = _RecordingContext()
        msg = self._leased_message(UNREGISTERED_WIRE_TYPE)

        _run(message_handler.handle_single_message(ctx, msg))

        self.assertFalse(self.source.holds_shared())
        self.assertEqual(len(ctx.written), 1)
        self.assertEqual(ctx.written[0].MESSAGE_NAME, "Failure")

    def test_a_filter_rejection_leaves_no_lease(self):
        def refuse(msg_type, handler):
            raise DataError("not for you")

        message_handler.filters.append(refuse)

        ctx = _RecordingContext()
        # A type that IS registered, so the refusal comes from the filter and not from lookup.
        msg = self._leased_message(MessageType.GetFeatures)

        _run(message_handler.handle_single_message(ctx, msg))

        self.assertFalse(self.source.holds_shared())
        self.assertEqual(ctx.written[0].MESSAGE_NAME, "Failure")

    def test_the_shared_buffer_is_usable_again_afterwards(self):
        """The property the two tests above are really about."""
        ctx = _RecordingContext()
        _run(
            message_handler.handle_single_message(
                ctx, self._leased_message(UNREGISTERED_WIRE_TYPE)
            )
        )

        other = CodecBufferSource(WireBuffer(0), self.shared)
        self.assertIsNotNone(other.get(512))


@unittest.skipUnless(not utils.USE_THP, "the codec buffer source exists only in a codec build")
class TestWriteUnderAHeldReadLease(unittest.TestCase):
    """A response must not be encoded over the request it is answering."""

    def test_a_write_does_not_disturb_a_message_still_holding_the_lease(self):
        shared = SharedBuffer(1024)
        source = CodecBufferSource(WireBuffer(0), shared)

        # A read in flight: `read` raised `UnexpectedMessageException` with the message undecoded,
        # so the loop writes a response while a `Message` still views the shared buffer.
        pending = source.get(256)
        self.assertIsNotNone(pending)
        for i in range(256):
            pending[i] = i & 0xFF
        expected = bytes(pending)

        ctx = CodecContext(MockHID(), source)
        gen = ctx.write(Failure(code=1, message="x" * 200))
        try:
            gen.send(None)
            while True:
                gen.send(ctx.iface.TX_PACKET_LEN)
        except StopIteration:
            pass

        # KEEPING THE LEASE WAS NEVER ENOUGH. `SharedBuffer.acquire` returns True for the holder
        # that already owns it, so the response used to be encoded into these very bytes.
        # The write really happened -- otherwise this test would pass by doing nothing.
        self.assertTrue(len(ctx.iface.data) > 0)
        self.assertEqual(bytes(pending), expected)
        self.assertTrue(source.holds_shared())


if __name__ == "__main__":
    unittest.main()
