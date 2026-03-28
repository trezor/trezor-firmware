# flake8: noqa: F403,F405
from common import *  # isort:skip

from typing import Any, Awaitable

if utils.USE_THP:
    import thp_common
    from mock_wire_interface import MockHID
    from trezor.loop import Timeout, race
    from trezor.wire.thp import ENCRYPTED, PacketHeader
    from trezor.wire.thp import alternating_bit_protocol as ABP
    from trezor.wire.thp.channel import _MAX_RETRANSMISSION_COUNT
    from trezor.wire.thp.interface_context import ThpContext


@unittest.skipUnless(utils.USE_THP, "only needed for THP")
class TestTrezorHostProtocolWriter(unittest.TestCase):
    def setUp(self):
        self.interface = MockHID()
        thp_ctx = ThpContext(self.interface)
        (self.ctx,) = thp_ctx._iface_ctxs

    def test_write_timeout(self):
        channel = thp_common.get_new_channel(self.interface)
        seq_bit = ABP.get_send_seq_bit(channel.channel_cache)

        task = channel.write_encrypted_payload(ENCRYPTED, b"PAYLOAD")
        race_obj = task.send(None)  # start the generator
        assert isinstance(race_obj, race)
        _wait_for_ack, write_loop = race_obj.children
        write_loop.send(None)  # start the generator

        for _ in range(_MAX_RETRANSMISSION_COUNT - 1):
            write_loop.send(None)  # complete write
            write_loop.send(None)  # complete sleep

        write_loop.send(None)  # complete write last time
        with self.assertRaises(Timeout) as ctx:
            write_loop.send(None)  # complete sleep & raise Timeout

        with self.assertRaises(Timeout):
            task.throw(ctx.value)  # re-raise timeout in `write_encrypted_payload`

        # next write should use the next `seq_bit` (see #6138)
        self.assertNotEqual(ABP.get_send_seq_bit(channel.channel_cache), seq_bit)

    def test_write_blocked(self):
        channel = thp_common.get_new_channel(self.interface)
        seq_bit = ABP.get_send_seq_bit(channel.channel_cache)

        task = channel.write_encrypted_payload(ENCRYPTED, b"PAYLOAD")
        race_obj = task.send(None)  # start the generator
        assert isinstance(race_obj, race)
        _wait_for_ack, write_loop = race_obj.children
        write_loop.send(None)  # start the generator

        # Re-transmit a few times
        for _ in range(3):
            write_loop.send(None)  # complete write
            write_loop.send(None)  # complete sleep

        with self.assertRaises(Timeout) as ctx:
            # timeout `_write_payload_once()` (as if `loop.sleep` has completed) using dummy "ticks" integer value
            write_loop.send(12345)

        with self.assertRaises(Timeout):
            task.throw(ctx.value)  # re-raise timeout in `write_encrypted_payload`

        # next write should use the next `seq_bit` (see #6138)
        self.assertNotEqual(ABP.get_send_seq_bit(channel.channel_cache), seq_bit)


if __name__ == "__main__":
    unittest.main()
