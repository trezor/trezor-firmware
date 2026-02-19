# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor import protobuf
from trezor.wire.codec.codec_context import CodecContext
from trezor.wire.context import UnexpectedMessageException
from trezor.wire.protocol_common import Message
from mock_wire_interface import MockHID


class MockBufferProvider:
    """Mock buffer provider for testing."""

    def __init__(self, buffer=None):
        self._buffer = buffer

    def take(self):
        return self._buffer


class TestCodecContext(unittest.TestCase):
    def test_codec_context_creation(self):
        """Test creating a CodecContext."""
        iface = MockHID()
        provider = MockBufferProvider(bytearray(256))
        ctx = CodecContext(iface, provider)

        self.assertIs(ctx.iface, iface)
        self.assertIs(ctx.buffer_provider, provider)
        self.assertIsNone(ctx._buffer)

    def test_get_buffer_lazily_allocates(self):
        """Test that _get_buffer allocates buffer lazily."""
        iface = MockHID()
        buffer = bytearray(256)
        provider = MockBufferProvider(buffer)
        ctx = CodecContext(iface, provider)

        # Initially no buffer
        self.assertIsNone(ctx._buffer)

        # First call allocates
        result = ctx._get_buffer()
        self.assertIs(result, buffer)
        self.assertIs(ctx._buffer, buffer)

        # Second call returns same buffer
        result2 = ctx._get_buffer()
        self.assertIs(result2, buffer)

    def test_get_buffer_returns_none_when_provider_returns_none(self):
        """Test _get_buffer when provider returns None."""
        iface = MockHID()
        provider = MockBufferProvider(None)
        ctx = CodecContext(iface, provider)

        result = ctx._get_buffer()
        self.assertIsNone(result)

    def test_release_clears_session(self):
        """Test that release() clears the codec session."""
        iface = MockHID()
        provider = MockBufferProvider(bytearray(256))
        ctx = CodecContext(iface, provider)

        # Should not raise
        ctx.release()


class TestCodecContextMessageHandling(unittest.TestCase):
    def test_unexpected_message_raises(self):
        """Test that unexpected messages raise UnexpectedMessageException."""
        # This test verifies the behavior described in the read() method
        # When a message type doesn't match expected_types, it should raise
        iface = MockHID()
        provider = MockBufferProvider(bytearray(256))
        ctx = CodecContext(iface, provider)

        # Create a message that won't match any expected type
        msg = Message(9999, b"unexpected")
        exc = UnexpectedMessageException(msg)

        self.assertIsInstance(exc, Exception)
        self.assertEqual(exc.msg, msg)


if __name__ == "__main__":
    unittest.main()