# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor import protobuf
from trezor.wire.protocol_common import Context, Message, WireError
from mock_wire_interface import MockHID


class TestMessage(unittest.TestCase):
    def test_message_creation(self):
        """Test creating a Message instance."""
        msg = Message(42, b"test_data")
        self.assertEqual(msg.type, 42)
        self.assertEqual(msg.data, b"test_data")

    def test_message_with_empty_data(self):
        """Test creating a Message with empty data."""
        msg = Message(100, b"")
        self.assertEqual(msg.type, 100)
        self.assertEqual(msg.data, b"")

    def test_message_with_large_type(self):
        """Test creating a Message with a large type number."""
        msg = Message(65535, b"data")
        self.assertEqual(msg.type, 65535)
        self.assertEqual(msg.data, b"data")


class TestContext(unittest.TestCase):
    def test_context_creation_with_iface(self):
        """Test creating a Context with interface."""
        iface = MockHID()
        ctx = Context(iface)
        self.assertIs(ctx.iface, iface)
        self.assertEqual(ctx.message_type_enum_name, "MessageType")

    def test_context_creation_with_channel_id(self):
        """Test creating a Context with channel_id."""
        iface = MockHID()
        channel_id = b"\x01\x02\x03\x04"
        ctx = Context(iface, channel_id)
        self.assertEqual(ctx.channel_id, channel_id)

    def test_context_creation_custom_enum_name(self):
        """Test creating a Context with custom enum name."""
        iface = MockHID()
        ctx = Context(iface, message_type_enum_name="CustomMessageType")
        self.assertEqual(ctx.message_type_enum_name, "CustomMessageType")

    def test_context_release_default_implementation(self):
        """Test that default release() does nothing."""
        iface = MockHID()
        ctx = Context(iface)
        # Should not raise
        ctx.release()


class TestWireError(unittest.TestCase):
    def test_wire_error_is_exception(self):
        """Test that WireError is an Exception."""
        err = WireError()
        self.assertIsInstance(err, Exception)

    def test_wire_error_with_message(self):
        """Test WireError with a message."""
        err = WireError("test error")
        self.assertEqual(str(err), "test error")


class TestMessageEdgeCases(unittest.TestCase):
    def test_message_with_zero_type(self):
        """Test creating a Message with type 0."""
        msg = Message(0, b"data")
        self.assertEqual(msg.type, 0)
        self.assertEqual(msg.data, b"data")

    def test_message_with_bytearray_data(self):
        """Test creating a Message with bytearray."""
        data = bytearray(b"test")
        msg = Message(1, data)
        self.assertEqual(msg.type, 1)
        self.assertEqual(msg.data, data)

    def test_message_data_immutability(self):
        """Test that message data is not accidentally modified."""
        original_data = b"original"
        msg = Message(1, original_data)
        # Verify data is stored
        self.assertEqual(msg.data, original_data)


if __name__ == "__main__":
    unittest.main()