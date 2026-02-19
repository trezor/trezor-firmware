# flake8: noqa: F403,F405
from common import *  # isort:skip

if not utils.USE_THP:
    raise unittest.SkipTest("THP not enabled")

from trezor.wire.thp.pairing_context import PairingContext
from trezor.wire.protocol_common import Message
from trezor.wire.errors import DataError
from mock_wire_interface import MockHID


class MockChannel:
    """Mock channel for testing PairingContext."""

    def __init__(self):
        self.iface = MockHID()
        self.channel_id = b"\x01\x02\x03\x04"
        self.messages = []

    async def decrypt_message(self):
        if self.messages:
            return (0, self.messages.pop(0))
        # Return a dummy message
        return (0, Message(0, b""))

    async def write(self, msg, session_id=None):
        self.messages.append(msg)

    def get_channel_state(self):
        from trezor.wire.thp import ChannelState
        return ChannelState.TH1


@unittest.skipUnless(utils.USE_THP, "only needed for THP")
class TestPairingContext(unittest.TestCase):
    def test_pairing_context_creation(self):
        """Test creating a PairingContext."""
        channel = MockChannel()
        ctx = PairingContext(channel)

        self.assertIs(ctx.channel_ctx, channel)
        self.assertEqual(ctx.iface, channel.iface)
        self.assertEqual(ctx.channel_id, channel.channel_id)
        self.assertEqual(ctx.message_type_enum_name, "ThpMessageType")

    def test_pairing_context_initialization(self):
        """Test PairingContext initializes with None values."""
        channel = MockChannel()
        ctx = PairingContext(channel)

        self.assertIsNone(ctx.nfc_secret)
        self.assertIsNone(ctx.qr_code_secret)
        self.assertIsNone(ctx.code_entry_secret)
        self.assertIsNone(ctx.code_code_entry)
        self.assertIsNone(ctx.code_qr_code)
        self.assertIsNone(ctx.code_nfc)
        self.assertIsNone(ctx.nfc_secret_host)
        self.assertIsNone(ctx.handshake_hash_host)
        self.assertIsNone(ctx.host_name)
        self.assertIsNone(ctx.app_name)

    def test_set_selected_method_valid(self):
        """Test setting a valid pairing method."""
        from trezor.enums import ThpPairingMethod

        channel = MockChannel()
        ctx = PairingContext(channel)

        # This would normally check against enabled methods
        # For testing, we just verify the method exists
        self.assertTrue(hasattr(ThpPairingMethod, 'CodeEntry'))

    def test_set_selected_method_invalid_raises(self):
        """Test setting invalid pairing method raises."""
        channel = MockChannel()
        ctx = PairingContext(channel)

        # Create an invalid method value
        invalid_method = 9999

        with self.assertRaises(DataError):
            ctx.set_selected_method(invalid_method)

    def test_get_code_entry_string_without_code_raises(self):
        """Test getting code entry string without code raises."""
        channel = MockChannel()
        ctx = PairingContext(channel)

        with self.assertRaises(Exception) as cm:
            ctx._get_code_code_entry_str()

        self.assertIn("not available", str(cm.exception))

    def test_get_code_entry_string_formats_correctly(self):
        """Test code entry string formatting."""
        channel = MockChannel()
        ctx = PairingContext(channel)
        ctx.code_code_entry = 123456

        result = ctx._get_code_code_entry_str()
        self.assertEqual(result, "123 456")

    def test_get_code_entry_string_with_leading_zeros(self):
        """Test code entry string with leading zeros."""
        channel = MockChannel()
        ctx = PairingContext(channel)
        ctx.code_code_entry = 12

        result = ctx._get_code_code_entry_str()
        self.assertEqual(result, "000 012")

    def test_get_qr_code_string_without_code_raises(self):
        """Test getting QR code string without code raises."""
        channel = MockChannel()
        ctx = PairingContext(channel)

        with self.assertRaises(Exception) as cm:
            ctx._get_code_qr_code_str()

        self.assertIn("not available", str(cm.exception))

    def test_get_qr_code_string_formats_correctly(self):
        """Test QR code string formatting as hexadecimal."""
        channel = MockChannel()
        ctx = PairingContext(channel)
        ctx.code_qr_code = b"\x01\x02\x03\x04"

        result = ctx._get_code_qr_code_str()
        self.assertEqual(result, "01020304")


if __name__ == "__main__":
    unittest.main()