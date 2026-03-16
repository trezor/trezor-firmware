# flake8: noqa: F403,F405
from common import *  # isort:skip
from typing import Callable

from mock import patch

if utils.USE_THP:
    import fixtures
    import thp_common
    from trezor import protobuf, wire
    from trezor.messages import Ping
    from trezor.wire.thp import channel as channel_module
    from trezor.wire.thp.memory_manager import _PROTOBUF_BUFFER_SIZE
    from trezor.wire.thp.writer import MAX_PAYLOAD_LEN

    def _encoded_len_patch(first_len: int) -> patch:
        """
        Patches `protobuf.encoded_length`:

        - the first call of `protobuf.encoded_length(msg)` returns `first_len`,
        - subsequent calls of `protobuf.encoded_length(msg)` return `trezorproto.encoded_length(msg)` (correct value).
        """

        def _patch_first_encoded_len(
            first_len: int,
        ) -> Callable[[protobuf.MessageType], int]:
            import trezorproto

            called = False

            def wrapper(msg: protobuf.MessageType) -> int:
                nonlocal called
                if not called:
                    called = True
                    return first_len
                return trezorproto.encoded_length(msg)

            return wrapper

        return patch(protobuf, "encoded_length", _patch_first_encoded_len(first_len))


@unittest.skipUnless(utils.USE_THP, "only needed for THP")
class TestTrezorHostProtocolChannel(unittest.TestCase):
    def setUp(self):
        thp_common.prepare_context()

    def test_reassembler_get_buffer(self):
        """
        Test request of a reassembly buffer (various sizes).
        """
        channel = thp_common.TrackedChannel()
        reassembler: channel_module.Reassembler = channel.reassembler
        read_buffer = reassembler.thp_read_buf
        # Check constant has not been modified
        self.assertEqual(_PROTOBUF_BUFFER_SIZE, 8192)

        # Should pass
        for buffer_len in (0, 5, 100, 4096, _PROTOBUF_BUFFER_SIZE):
            buffer = read_buffer.get(buffer_len)
            assert buffer is not None  # to make typechecker happy
            self.assertEqual(len(buffer), buffer_len)

        # Should fail
        for buffer_len in (-1, -5, -100):
            with self.assertRaises(AssertionError):
                buffer = read_buffer.get(buffer_len)

        # Should return None
        for buffer_len in (
            _PROTOBUF_BUFFER_SIZE + 1,
            2 * _PROTOBUF_BUFFER_SIZE,
            2 * _PROTOBUF_BUFFER_SIZE + 1,
            MAX_PAYLOAD_LEN,  # Currently holds that: _PROTOBUF_BUFFER_SIZE < MAX_PAYLOAD_LEN
        ):
            buffer = read_buffer.get(buffer_len)
            self.assertIsNone(buffer)

    def test_write_too_big_message_mocked_size(self):
        """
        Action: Try to send a message with size greater than `MAX_PAYLOAD_LEN`. The size of the message is mocked.

        Expected: FirmwareError is raised.
        """
        channel = thp_common.TrackedChannel()
        gen = channel.write(Ping(message="Test"), 0)
        with _encoded_len_patch(first_len=MAX_PAYLOAD_LEN):
            with self.assertRaises(wire.FirmwareError) as e:
                gen.send(None)
            self.assertEqual(
                e.value.message,
                "Failed to write, message is too big.",
            )

    def test_write_big_message_mocked_size_pass(self):
        """
        Action: Try to send a message with size greater than `_PROTOBUF_BUFFER_SIZE`,
                but smaller than `MAX_PAYLOAD_LEN`. The size of the message is mocked.

        Expected: Message is sent successfully.
        """
        channel = thp_common.TrackedChannel()
        ping_message = "This message should be sent"
        gen = channel.write(Ping(message=ping_message), 0)
        with _encoded_len_patch(first_len=MAX_PAYLOAD_LEN - 1000):
            with channel:
                channel.set_expected_messages_to_write([Ping])
                gen.send(None)
                gen.send(None)

            # Check expected Ping
            assert Ping.is_type_of(channel.messages_to_write[-1])
            self.assertEqual(channel.messages_to_write[-1].message, ping_message)

    def test_write_big_message_mocked_size_fail(self):
        """
        Action: Try to send a message with size greater than `_PROTOBUF_BUFFER_SIZE`,
                but smaller than `MAX_PAYLOAD_LEN`. The size of the message is mocked
                and the `MAX_PAYLOAD_LEN` is increased to ensure that the allocation fails.

        Expected: FirmwareError is raised.
        """
        channel = thp_common.TrackedChannel()
        ping_message = "This message should fail to be sent"
        gen = channel.write(Ping(message=ping_message), 0)
        mock_max_payload_len = 999999999
        with patch(channel_module, "MAX_PAYLOAD_LEN", mock_max_payload_len):
            with _encoded_len_patch(first_len=mock_max_payload_len - 1000):
                with self.assertRaises(wire.FirmwareError) as e:
                    gen.send(None)
                self.assertEqual(
                    e.value.message,
                    "Failed to allocate a sufficiently large write buffer.",
                )

    def test_write_big_message(self):
        """
        Action: Try to send a message with size greater than `_PROTOBUF_BUFFER_SIZE`,
                but smaller than `MAX_PAYLOAD_LEN`. The size of the message is real.

        Expected: Message is sent successfully.
        """
        channel = thp_common.TrackedChannel()
        ping_message = fixtures.LONG_STRING_50000
        gen = channel.write(Ping(message=ping_message), 0)
        with channel:
            channel.set_expected_messages_to_write([Ping])
            gen.send(None)
            gen.send(None)

        # Check expected Ping
        assert Ping.is_type_of(channel.messages_to_write[-1])
        self.assertEqual(channel.messages_to_write[-1].message, ping_message)


if __name__ == "__main__":
    unittest.main()
