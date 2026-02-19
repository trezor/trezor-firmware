# flake8: noqa: F403,F405
from common import *  # isort:skip

from mock import Mock
from trezor.wire.protocol_common import Context, Message, WireError


class TestMessage(unittest.TestCase):
    def test_message_initialization(self):
        """Test Message initialization with type and data."""
        msg = Message(42, b"test_data")

        self.assertEqual(msg.type, 42)
        self.assertEqual(msg.data, b"test_data")

    def test_message_with_empty_data(self):
        """Test Message with empty data."""
        msg = Message(1, b"")

        self.assertEqual(msg.type, 1)
        self.assertEqual(msg.data, b"")

    def test_message_with_large_type(self):
        """Test Message with large type value."""
        msg = Message(0xFFFF, b"data")

        self.assertEqual(msg.type, 0xFFFF)

    def test_message_with_bytearray_data(self):
        """Test Message with bytearray data."""
        data = bytearray(b"test")
        msg = Message(1, data)

        self.assertEqual(msg.data, data)


class TestContext(unittest.TestCase):
    def test_context_initialization(self):
        """Test Context initialization."""
        iface = Mock()
        ctx = Context(iface)

        self.assertEqual(ctx.iface, iface)
        self.assertEqual(ctx.message_type_enum_name, "MessageType")

    def test_context_with_channel_id(self):
        """Test Context initialization with channel_id."""
        iface = Mock()
        channel_id = b"\x01\x02\x03\x04"
        ctx = Context(iface, channel_id)

        self.assertEqual(ctx.channel_id, channel_id)

    def test_context_with_custom_message_type_enum(self):
        """Test Context with custom message type enum name."""
        iface = Mock()
        ctx = Context(iface, message_type_enum_name="CustomMessageType")

        self.assertEqual(ctx.message_type_enum_name, "CustomMessageType")

    def test_context_release_default_implementation(self):
        """Test that release() default implementation does nothing."""
        iface = Mock()
        ctx = Context(iface)

        # Should not raise
        ctx.release()


class TestWireError(unittest.TestCase):
    def test_wire_error_is_exception(self):
        """Test that WireError is an Exception."""
        self.assertTrue(issubclass(WireError, Exception))

    def test_wire_error_can_be_raised(self):
        """Test that WireError can be raised."""
        with self.assertRaises(WireError):
            raise WireError("test error")

    def test_wire_error_with_message(self):
        """Test WireError with message."""
        try:
            raise WireError("custom message")
        except WireError as e:
            self.assertEqual(str(e), "custom message")


class TestMessageEdgeCases(unittest.TestCase):
    def test_message_type_zero(self):
        """Test Message with type 0."""
        msg = Message(0, b"data")
        self.assertEqual(msg.type, 0)

    def test_message_with_large_data(self):
        """Test Message with large data payload."""
        large_data = b"x" * 10000
        msg = Message(1, large_data)

        self.assertEqual(len(msg.data), 10000)
        self.assertEqual(msg.data, large_data)

    def test_message_with_memoryview(self):
        """Test Message with memoryview data."""
        data = memoryview(b"test_data")
        msg = Message(1, data)

        # Should store the memoryview
        self.assertEqual(bytes(msg.data), b"test_data")


class TestContextEdgeCases(unittest.TestCase):
    def test_context_without_channel_id(self):
        """Test Context without explicitly setting channel_id."""
        iface = Mock()
        ctx = Context(iface)

        # channel_id should not be set in __init__ if not provided
        # but the class has it as an attribute annotation

    def test_context_with_none_channel_id(self):
        """Test Context explicitly passed None for channel_id."""
        iface = Mock()
        ctx = Context(iface, channel_id=None)

        # Should initialize without setting channel_id attribute

    def test_context_with_empty_channel_id(self):
        """Test Context with empty bytes for channel_id."""
        iface = Mock()
        channel_id = b""
        ctx = Context(iface, channel_id)

        self.assertEqual(ctx.channel_id, b"")

    def test_multiple_contexts_same_interface(self):
        """Test multiple Context instances with same interface."""
        iface = Mock()
        ctx1 = Context(iface, b"\x01")
        ctx2 = Context(iface, b"\x02")

        self.assertEqual(ctx1.iface, ctx2.iface)
        self.assertNotEqual(ctx1.channel_id, ctx2.channel_id)


if __name__ == "__main__":
    unittest.main()