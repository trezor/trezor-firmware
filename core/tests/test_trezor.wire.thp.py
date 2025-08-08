# flake8: noqa: F403,F405
from common import *  # isort:skip
from mock_wire_interface import MockHID
from trezor import io

if utils.USE_THP:
    import thp_common
    from trezor.wire import handle_session as thp_main_loop
    from trezor.wire.thp import memory_manager


@unittest.skipUnless(utils.USE_THP, "only needed for THP")
class TestTrezorHostProtocol(unittest.TestCase):

    def __init__(self):
        if __debug__:
            thp_common.suppress_debug_log()
        super().__init__()

    def setUp(self):
        self.interface = MockHID()
        memory_manager.READ_BUFFER = bytearray(64)
        memory_manager.WRITE_BUFFER = bytearray(256)

    def test_codec_message(self):
        self.assertEqual(len(self.interface.data), 0)
        gen = thp_main_loop(self.interface)
        gen.send(None)

        # There should be a failiure response to received init packet (starts with "?##")
        test_codec_message = b"?## Some data"
        self.interface.mock_read(test_codec_message, gen)
        gen.send(None)
        self.assertEqual(len(self.interface.data), 1)

        expected_response = b"?##\x00\x03\x00\x00\x00\x14\x08\x11"
        self.assertEqual(
            self.interface.data[-1][: len(expected_response)], expected_response
        )

        # There should be no response for continuation packet (starts with "?" only)
        test_codec_message_2 = b"? Cont packet"
        self.interface.mock_read(test_codec_message_2, gen)

        # Check that sending None fails on AssertionError
        with self.assertRaises(AssertionError):
            gen.send(None)
        self.assertEqual(len(self.interface.data), 1)

    def test_message_on_unallocated_channel(self):
        gen = thp_main_loop(self.interface)
        query = gen.send(None)
        self.assertObjectEqual(query, self.interface.wait_object(io.POLL_READ))
        message_to_channel_789a = (
            b"\x04\x78\x9a\x00\x0c\x00\x11\x22\x33\x44\x55\x66\x77\x96\x64\x3c\x6c"
        )
        self.interface.mock_read(message_to_channel_789a, gen)
        gen.send(None)
        unallocated_chanel_error_on_channel_789a = "42789a0005027b743563000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
        self.assertEqual(
            utils.hexlify_if_bytes(self.interface.data[-1]),
            unallocated_chanel_error_on_channel_789a,
        )


if __name__ == "__main__":
    unittest.main()
