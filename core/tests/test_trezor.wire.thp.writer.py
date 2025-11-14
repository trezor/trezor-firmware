# flake8: noqa: F403,F405
from common import *  # isort:skip

from typing import Any, Awaitable

if utils.USE_THP:
    import thp_common
    from mock_wire_interface import MockHID
    from trezor.loop import Timeout
    from trezor.wire.thp import ENCRYPTED, PacketHeader
    from trezor.wire.thp import alternating_bit_protocol as ABP
    from trezor.wire.thp.channel import _MAX_RETRANSMISSION_COUNT
    from trezor.wire.thp.interface_context import ThpContext


@unittest.skipUnless(utils.USE_THP, "only needed for THP")
class TestTrezorHostProtocolWriter(unittest.TestCase):
    short_payload_expected = b"04123400050700000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
    longer_payload_expected = [
        b"0412340100000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a",
        b"8012343b3c3d3e3f404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f606162636465666768696a6b6c6d6e6f7071727374757677",
        b"80123478797a7b7c7d7e7f808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9fa0a1a2a3a4a5a6a7a8a9aaabacadaeafb0b1b2b3b4",
        b"801234b5b6b7b8b9babbbcbdbebfc0c1c2c3c4c5c6c7c8c9cacbcccdcecfd0d1d2d3d4d5d6d7d8d9dadbdcdddedfe0e1e2e3e4e5e6e7e8e9eaebecedeeeff0f1",
        b"801234f2f3f4f5f6f7f8f9fafbfcfdfeff0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
    ]
    eight_longer_payloads_expected = [
        b"0412340800000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a",
        b"8012343b3c3d3e3f404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f606162636465666768696a6b6c6d6e6f7071727374757677",
        b"80123478797a7b7c7d7e7f808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9fa0a1a2a3a4a5a6a7a8a9aaabacadaeafb0b1b2b3b4",
        b"801234b5b6b7b8b9babbbcbdbebfc0c1c2c3c4c5c6c7c8c9cacbcccdcecfd0d1d2d3d4d5d6d7d8d9dadbdcdddedfe0e1e2e3e4e5e6e7e8e9eaebecedeeeff0f1",
        b"801234f2f3f4f5f6f7f8f9fafbfcfdfeff000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e",
        b"8012342f303132333435363738393a3b3c3d3e3f404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f606162636465666768696a6b",
        b"8012346c6d6e6f707172737475767778797a7b7c7d7e7f808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9fa0a1a2a3a4a5a6a7a8",
        b"801234a9aaabacadaeafb0b1b2b3b4b5b6b7b8b9babbbcbdbebfc0c1c2c3c4c5c6c7c8c9cacbcccdcecfd0d1d2d3d4d5d6d7d8d9dadbdcdddedfe0e1e2e3e4e5",
        b"801234e6e7e8e9eaebecedeeeff0f1f2f3f4f5f6f7f8f9fafbfcfdfeff000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122",
        b"801234232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f",
        b"801234606162636465666768696a6b6c6d6e6f707172737475767778797a7b7c7d7e7f808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c",
        b"8012349d9e9fa0a1a2a3a4a5a6a7a8a9aaabacadaeafb0b1b2b3b4b5b6b7b8b9babbbcbdbebfc0c1c2c3c4c5c6c7c8c9cacbcccdcecfd0d1d2d3d4d5d6d7d8d9",
        b"801234dadbdcdddedfe0e1e2e3e4e5e6e7e8e9eaebecedeeeff0f1f2f3f4f5f6f7f8f9fafbfcfdfeff000102030405060708090a0b0c0d0e0f10111213141516",
        b"8012341718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f404142434445464748494a4b4c4d4e4f50515253",
        b"8012345455565758595a5b5c5d5e5f606162636465666768696a6b6c6d6e6f707172737475767778797a7b7c7d7e7f808182838485868788898a8b8c8d8e8f90",
        b"8012349192939495969798999a9b9c9d9e9fa0a1a2a3a4a5a6a7a8a9aaabacadaeafb0b1b2b3b4b5b6b7b8b9babbbcbdbebfc0c1c2c3c4c5c6c7c8c9cacbcccd",
        b"801234cecfd0d1d2d3d4d5d6d7d8d9dadbdcdddedfe0e1e2e3e4e5e6e7e8e9eaebecedeeeff0f1f2f3f4f5f6f7f8f9fafbfcfdfeff000102030405060708090a",
        b"8012340b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f4041424344454647",
        b"80123448494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f606162636465666768696a6b6c6d6e6f707172737475767778797a7b7c7d7e7f8081828384",
        b"80123485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9fa0a1a2a3a4a5a6a7a8a9aaabacadaeafb0b1b2b3b4b5b6b7b8b9babbbcbdbebfc0c1",
        b"801234c2c3c4c5c6c7c8c9cacbcccdcecfd0d1d2d3d4d5d6d7d8d9dadbdcdddedfe0e1e2e3e4e5e6e7e8e9eaebecedeeeff0f1f2f3f4f5f6f7f8f9fafbfcfdfe",
        b"801234ff000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a3b",
        b"8012343c3d3e3f404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f606162636465666768696a6b6c6d6e6f707172737475767778",
        b"801234797a7b7c7d7e7f808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9fa0a1a2a3a4a5a6a7a8a9aaabacadaeafb0b1b2b3b4b5",
        b"801234b6b7b8b9babbbcbdbebfc0c1c2c3c4c5c6c7c8c9cacbcccdcecfd0d1d2d3d4d5d6d7d8d9dadbdcdddedfe0e1e2e3e4e5e6e7e8e9eaebecedeeeff0f1f2",
        b"801234f3f4f5f6f7f8f9fafbfcfdfeff000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f",
        b"801234303132333435363738393a3b3c3d3e3f404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f606162636465666768696a6b6c",
        b"8012346d6e6f707172737475767778797a7b7c7d7e7f808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9fa0a1a2a3a4a5a6a7a8a9",
        b"801234aaabacadaeafb0b1b2b3b4b5b6b7b8b9babbbcbdbebfc0c1c2c3c4c5c6c7c8c9cacbcccdcecfd0d1d2d3d4d5d6d7d8d9dadbdcdddedfe0e1e2e3e4e5e6",
        b"801234e7e8e9eaebecedeeeff0f1f2f3f4f5f6f7f8f9fafbfcfdfeff000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20212223",
        b"8012342425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f60",
        b"8012346162636465666768696a6b6c6d6e6f707172737475767778797a7b7c7d7e7f808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d",
        b"8012349e9fa0a1a2a3a4a5a6a7a8a9aaabacadaeafb0b1b2b3b4b5b6b7b8b9babbbcbdbebfc0c1c2c3c4c5c6c7c8c9cacbcccdcecfd0d1d2d3d4d5d6d7d8d9da",
        b"801234dbdcdddedfe0e1e2e3e4e5e6e7e8e9eaebecedeeeff0f1f2f3f4f5f6f7f8f9fafbfcfdfeff000000000000000000000000000000000000000000000000",
    ]
    empty_payload_with_checksum_expected = b"0412340004edbd479c00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
    longer_payload_with_checksum_expected = [
        b"0412340100000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a",
        b"8012343b3c3d3e3f404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f606162636465666768696a6b6c6d6e6f7071727374757677",
        b"80123478797a7b7c7d7e7f808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9fa0a1a2a3a4a5a6a7a8a9aaabacadaeafb0b1b2b3b4",
        b"801234b5b6b7b8b9babbbcbdbebfc0c1c2c3c4c5c6c7c8c9cacbcccdcecfd0d1d2d3d4d5d6d7d8d9dadbdcdddedfe0e1e2e3e4e5e6e7e8e9eaebecedeeeff0f1",
        b"801234f2f3f4f5f6f7f8f9fafbfcfdfefff40c65ee00000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
    ]

    def await_until_result(self, task: Awaitable) -> Any:
        with self.assertRaises(StopIteration):
            while True:
                task.send(None)

    def __init__(self):
        if __debug__:
            thp_common.suppress_debug_log()
        super().__init__()

    def setUp(self):
        self.interface = MockHID()
        thp_ctx = ThpContext(self.interface)
        (self.ctx,) = thp_ctx._iface_ctxs

    def test_write_empty_payload(self):
        header = PacketHeader(ENCRYPTED, 4660, 4)
        await_result(self.ctx._write_payload_chunks(header, b""))
        self.assertEqual(len(self.interface.data), 0)

    def test_write_short_payload(self):
        header = PacketHeader(ENCRYPTED, 4660, 5)
        data = b"\x07"
        self.await_until_result(self.ctx._write_payload_chunks(header, data))
        self.assertEqual(hexlify(self.interface.data[0]), self.short_payload_expected)

    def test_write_longer_payload(self):
        data = bytearray(range(256))
        header = PacketHeader(ENCRYPTED, 4660, 256)
        self.await_until_result(self.ctx._write_payload_chunks(header, data))

        for i in range(len(self.longer_payload_expected)):
            self.assertEqual(
                hexlify(self.interface.data[i]), self.longer_payload_expected[i]
            )

    def test_write_eight_longer_payloads(self):
        data = bytearray(range(256))
        header = PacketHeader(ENCRYPTED, 4660, 2048)
        chunks = [data] * 8
        self.await_until_result(self.ctx._write_payload_chunks(header, *chunks))

        for i in range(len(self.eight_longer_payloads_expected)):
            self.assertEqual(
                hexlify(self.interface.data[i]), self.eight_longer_payloads_expected[i]
            )

    def test_write_empty_payload_with_checksum(self):
        header = PacketHeader(ENCRYPTED, 4660, 4)
        self.await_until_result(self.ctx.write_payload(header, b""))

        self.assertEqual(
            hexlify(self.interface.data[0]), self.empty_payload_with_checksum_expected
        )

    def test_write_longer_payload_with_checksum(self):
        data = bytearray(range(256))
        header = PacketHeader(ENCRYPTED, 4660, 256)
        self.await_until_result(self.ctx.write_payload(header, data))

        for i in range(len(self.longer_payload_with_checksum_expected)):
            self.assertEqual(
                hexlify(self.interface.data[i]),
                self.longer_payload_with_checksum_expected[i],
            )

    def test_write_timeout(self):
        channel = thp_common.get_new_channel(self.interface)
        seq_bit = ABP.get_send_seq_bit(channel.channel_cache)

        task = channel.write_encrypted_payload(ENCRYPTED, b"PAYLOAD")
        task.send(None)  # start the generator

        for _ in range(_MAX_RETRANSMISSION_COUNT - 1):
            task.send(None)  # complete write
            task.throw(Timeout())  # no ACK is received

        task.send(None)  # complete write last time
        with self.assertRaises(Timeout):
            task.throw(Timeout())  # no ACK is received

        # next write should use the next `seq_bit` (see #6138)
        self.assertNotEqual(ABP.get_send_seq_bit(channel.channel_cache), seq_bit)

    def test_write_blocked(self):
        channel = thp_common.get_new_channel(self.interface)
        seq_bit = ABP.get_send_seq_bit(channel.channel_cache)

        task = channel.write_encrypted_payload(ENCRYPTED, b"PAYLOAD")
        task.send(None)  # start the generator

        # Re-transmit a few times
        for _ in range(3):
            task.send(None)  # complete write
            task.throw(Timeout())  # no ACK is received

        with self.assertRaises(Timeout):
            # timeout write (as if `loop.sleep` has completed) using dummy "ticks" integer value
            task.send(12345)

        # next write should use the next `seq_bit` (see #6138)
        self.assertNotEqual(ABP.get_send_seq_bit(channel.channel_cache), seq_bit)


if __name__ == "__main__":
    unittest.main()
