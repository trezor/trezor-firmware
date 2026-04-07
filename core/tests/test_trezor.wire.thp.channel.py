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
    from trezor.wire.thp.channel import Reassembler
    from trezor.wire.thp.memory_manager import _PROTOBUF_BUFFER_SIZE, ThpBuffer
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
class TestTrezorHostProtocolChannel(TestCaseWithContext):
    def test_reassembler_get_buffer(self):
        """
        Test request of a reassembly buffer (various sizes).
        """
        reassembler = Reassembler(ThpBuffer())
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
        Action: Try to send a message with size greater than `_PROTOBUF_BUFFER_SIZE`. The size of the message is mocked.

        Expected: FirmwareError is raised.
        """
        channel = thp_common.PatchedChannel()
        gen = channel.write(Ping(message="Test"), 0)
        with _encoded_len_patch(first_len=_PROTOBUF_BUFFER_SIZE + 1):
            with self.assertRaises(wire.FirmwareError) as e:
                gen.send(None)
            self.assertEqual(
                e.value.message,
                "Failed to get a sufficiently large write buffer.",
            )

    def test_write_too_big_message(self):
        """
        Action: Try to send a message with size greater than `_PROTOBUF_BUFFER_SIZE`,
                but smaller than `MAX_PAYLOAD_LEN`. The size of the message is real.

        Expected: Message is sent successfully.
        """
        channel = thp_common.PatchedChannel()
        ping_message = fixtures.LONG_STRING_50000
        gen = channel.write(Ping(message=ping_message), 0)
        with self.assertRaises(wire.FirmwareError) as e:
            gen.send(None)
        self.assertEqual(
            e.value.message,
            "Failed to get a sufficiently large write buffer.",
        )


if __name__ == "__main__":
    unittest.main()
