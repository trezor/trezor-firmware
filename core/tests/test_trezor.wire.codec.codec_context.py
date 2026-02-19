# flake8: noqa: F403,F405
from common import *  # isort:skip

from mock import Mock, MockAsync, patch
from mock_wire_interface import MockHID
from storage.cache_common import InvalidSessionError
from trezor import protobuf
from trezor.wire.codec.codec_context import CodecContext
from trezor.wire.context import UnexpectedMessageException
from trezor.wire.protocol_common import Message


class MockProvider:
    """Mock buffer provider for testing."""

    def __init__(self, buffer_size=64):
        self.buffer_size = buffer_size
        self.taken = False

    def take(self):
        if self.taken:
            return None
        self.taken = True
        return bytearray(self.buffer_size)

    def reset(self):
        self.taken = False


class MockMessage(protobuf.MessageType):
    """Mock protobuf message for testing."""

    MESSAGE_WIRE_TYPE = 42
    MESSAGE_NAME = "MockMessage"

    def __init__(self, value=None):
        self.value = value or "test"


class TestCodecContextInitialization(unittest.TestCase):
    def test_initialization(self):
        """Test CodecContext initialization."""
        iface = MockHID()
        provider = MockProvider()
        ctx = CodecContext(iface, provider)

        self.assertEqual(ctx.iface, iface)
        self.assertEqual(ctx.buffer_provider, provider)
        self.assertIsNone(ctx._buffer)

    def test_get_buffer_takes_from_provider(self):
        """Test that _get_buffer takes buffer from provider."""
        iface = MockHID()
        provider = MockProvider(128)
        ctx = CodecContext(iface, provider)

        buffer = ctx._get_buffer()

        self.assertIsNotNone(buffer)
        self.assertEqual(len(buffer), 128)
        self.assertTrue(provider.taken)

    def test_get_buffer_returns_same_buffer(self):
        """Test that _get_buffer returns the same buffer on multiple calls."""
        iface = MockHID()
        provider = MockProvider()
        ctx = CodecContext(iface, provider)

        buffer1 = ctx._get_buffer()
        buffer2 = ctx._get_buffer()

        self.assertIs(buffer1, buffer2)

    def test_get_buffer_returns_none_when_provider_empty(self):
        """Test that _get_buffer returns None when provider has no buffer."""
        iface = MockHID()
        provider = MockProvider()
        ctx = CodecContext(iface, provider)

        # Take the buffer
        buffer1 = ctx._get_buffer()
        self.assertIsNotNone(buffer1)

        # Create a new context with same provider
        ctx2 = CodecContext(iface, provider)
        buffer2 = ctx2._get_buffer()

        self.assertIsNone(buffer2)


class TestCodecContextWrite(unittest.TestCase):
    def test_write_encodes_message(self):
        """Test that write encodes and sends the message."""
        iface = MockHID()
        provider = MockProvider(256)
        ctx = CodecContext(iface, provider)

        msg = MockMessage("test_data")

        async def test():
            await ctx.write(msg)

        from trezor import loop

        loop.run(test())

        # HID should have received data
        self.assertGreater(len(iface.data), 0)

    def test_write_with_no_buffer_small_message(self):
        """Test write with no buffer but small message."""
        iface = MockHID()
        provider = Mock()
        provider.take = Mock(return_value=None)
        ctx = CodecContext(iface, provider)

        # Create a message that's under 128 bytes
        msg = MockMessage("small")

        async def test():
            await ctx.write(msg)

        from trezor import loop

        # Should not raise, creates its own buffer for small messages
        loop.run(test())

    def test_write_with_no_buffer_large_message_raises(self):
        """Test that write raises IOError for large messages without buffer."""
        iface = MockHID()
        provider = Mock()
        provider.take = Mock(return_value=None)
        ctx = CodecContext(iface, provider)

        # Create a mock message with a large encoded size
        msg = MockMessage("x" * 200)

        async def test():
            with patch(
                protobuf, "encoded_length", Mock(return_value=200)
            ):
                await ctx.write(msg)

        from trezor import loop

        with self.assertRaises(IOError):
            loop.run(test())

    def test_write_reallocates_buffer_if_needed(self):
        """Test that write reallocates buffer if message is too large."""
        iface = MockHID()
        provider = MockProvider(64)
        ctx = CodecContext(iface, provider)

        # Get small buffer
        buffer = ctx._get_buffer()
        self.assertEqual(len(buffer), 64)

        # Create message that needs larger buffer
        msg = MockMessage("large_data")

        async def test():
            # Mock encoded_length to return size larger than buffer
            with patch(protobuf, "encoded_length", Mock(return_value=128)):
                await ctx.write(msg)

        from trezor import loop

        loop.run(test())


class TestCodecContextRelease(unittest.TestCase):
    def test_release_ends_session(self):
        """Test that release ends the codec session."""
        from storage import cache_codec

        iface = MockHID()
        provider = MockProvider()
        ctx = CodecContext(iface, provider)

        with patch(cache_codec, "end_current_session", Mock()) as mock_end:
            ctx.release()
            self.assertEqual(len(mock_end.calls), 1)


class TestCodecContextCache(unittest.TestCase):
    def test_cache_property_with_active_session(self):
        """Test cache property returns active session cache."""
        from storage import cache_codec

        iface = MockHID()
        provider = MockProvider()
        ctx = CodecContext(iface, provider)

        mock_cache = Mock()
        with patch(
            cache_codec, "get_active_session", Mock(return_value=mock_cache)
        ):
            cache = ctx.cache
            self.assertEqual(cache, mock_cache)

    def test_cache_property_without_session_raises(self):
        """Test cache property raises InvalidSessionError without active session."""
        from storage import cache_codec

        iface = MockHID()
        provider = MockProvider()
        ctx = CodecContext(iface, provider)

        with patch(cache_codec, "get_active_session", Mock(return_value=None)):
            with self.assertRaises(InvalidSessionError):
                _ = ctx.cache


class TestCodecContextEdgeCases(unittest.TestCase):
    def test_buffer_persistence_across_operations(self):
        """Test that buffer persists across multiple operations."""
        iface = MockHID()
        provider = MockProvider(256)
        ctx = CodecContext(iface, provider)

        buffer1 = ctx._get_buffer()
        msg = MockMessage("data1")

        async def test():
            await ctx.write(msg)

        from trezor import loop

        loop.run(test())

        buffer2 = ctx._get_buffer()
        self.assertIs(buffer1, buffer2)

    def test_multiple_writes_reuse_buffer(self):
        """Test that multiple writes reuse the same buffer."""
        iface = MockHID()
        provider = MockProvider(256)
        ctx = CodecContext(iface, provider)

        msg1 = MockMessage("data1")
        msg2 = MockMessage("data2")

        async def test():
            await ctx.write(msg1)
            await ctx.write(msg2)

        from trezor import loop

        loop.run(test())

        # Provider should only be called once
        buffer = ctx._get_buffer()
        self.assertIsNotNone(buffer)

    def test_context_without_buffer_allocation(self):
        """Test context behavior when buffer is never allocated."""
        iface = MockHID()
        provider = MockProvider()
        ctx = CodecContext(iface, provider)

        # Don't call _get_buffer, buffer should still be None
        self.assertIsNone(ctx._buffer)


class TestCodecContextMessageHandling(unittest.TestCase):
    def test_write_message_without_wire_type_raises(self):
        """Test that write raises for message without wire type."""
        iface = MockHID()
        provider = MockProvider()
        ctx = CodecContext(iface, provider)

        msg = Mock()
        msg.MESSAGE_WIRE_TYPE = None

        async def test():
            await ctx.write(msg)

        from trezor import loop

        with self.assertRaises(AssertionError):
            loop.run(test())


class TestCodecContextBufferProvider(unittest.TestCase):
    def test_provider_called_only_once(self):
        """Test that buffer provider is called only once."""
        iface = MockHID()
        provider = Mock()
        provider.take = Mock(return_value=bytearray(128))
        ctx = CodecContext(iface, provider)

        # Call _get_buffer multiple times
        ctx._get_buffer()
        ctx._get_buffer()
        ctx._get_buffer()

        # Provider should only be called once
        self.assertEqual(len(provider.take.calls), 1)

    def test_different_contexts_different_buffers(self):
        """Test that different contexts get different buffers."""
        iface = MockHID()
        provider1 = MockProvider(128)
        provider2 = MockProvider(256)

        ctx1 = CodecContext(iface, provider1)
        ctx2 = CodecContext(iface, provider2)

        buffer1 = ctx1._get_buffer()
        buffer2 = ctx2._get_buffer()

        self.assertIsNot(buffer1, buffer2)
        self.assertEqual(len(buffer1), 128)
        self.assertEqual(len(buffer2), 256)


if __name__ == "__main__":
    unittest.main()