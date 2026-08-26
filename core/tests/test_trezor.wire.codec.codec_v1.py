# flake8: noqa: F403,F405
from common import *  # isort:skip

import struct

from mock_wire_interface import MockHID
from trezor import io
from trezor.utils import chunks
from trezor.wire.buffers import SharedBuffer, WireBuffer
from trezor.wire.codec import codec_v1
from trezor.wire.codec.buffers import CodecBufferSource, private_source
from trezor.wire.protocol_common import WireError

MESSAGE_TYPE = 0x4242

HEADER_PAYLOAD_LENGTH = MockHID.RX_PACKET_LEN - 3 - struct.calcsize(">HL")


def make_header(mtype, length):
    return b"?##" + struct.pack(">HL", mtype, length)


def make_source(size):
    """A source with `size` bytes of its own and nothing shared, plus a view of that memory."""
    small = WireBuffer(size)
    return CodecBufferSource(small), small.buf


class TestWireCodecV1(unittest.TestCase):
    def setUp(self):
        self.interface = MockHID()

    def test_read_one_packet(self):
        # zero length message - just a header
        message_packet = make_header(mtype=MESSAGE_TYPE, length=0)
        buffers, buffer = make_source(64)

        gen = codec_v1.read_message(self.interface, buffers)

        query = gen.send(None)
        self.assertObjectEqual(query, self.interface.wait_object(io.POLL_READ))

        with self.assertRaises(StopIteration) as e:
            self.interface.mock_read(message_packet, gen)

        # e.value is StopIteration. e.value.value is the return value of the call
        result = e.value.value
        self.assertEqual(result.type, MESSAGE_TYPE)
        self.assertEqual(result.data, b"")

        # message should have been read into the buffer
        self.assertEqual(bytes(buffer), b"\x00" * 64)

    def test_read_while_the_shared_buffer_is_busy(self):
        """The refusal that used to come from a spent `Provider`, now decided per message.

        `WireError` rather than `CodecError` on purpose: it does not terminate the session, so the
        interface can still answer with a `Failure` saying exactly this.
        """
        shared = SharedBuffer(64)
        incumbent = CodecBufferSource(WireBuffer(0), shared)
        self.assertIsNotNone(incumbent.get(32))

        message_packet = make_header(mtype=MESSAGE_TYPE, length=32)
        gen = codec_v1.read_message(
            self.interface, CodecBufferSource(WireBuffer(0), shared)
        )

        query = gen.send(None)
        self.assertObjectEqual(query, self.interface.wait_object(io.POLL_READ))

        with self.assertRaises(WireError):
            self.interface.mock_read(message_packet, gen)

    def _packets_for(self, message):
        header = make_header(mtype=MESSAGE_TYPE, length=len(message))
        return [header + message[:HEADER_PAYLOAD_LENGTH]] + [
            b"?" + chunk
            for chunk in chunks(
                message[HEADER_PAYLOAD_LENGTH:], MockHID.RX_PACKET_LEN - 1
            )
        ]

    def test_a_refused_message_is_drained_before_the_refusal(self):
        """The refusal above, made on a message that does not fit in one packet.

        THE SINGLE-PACKET TEST COULD NOT SEE THIS. The initial report is consumed before the
        buffer is asked for, so refusing there left this message's continuation reports on the
        wire -- and the next read parsed one of them as a header, failed `Invalid magic`, and did
        it again for every packet. The oversize path had always drained for exactly this reason.
        """
        shared = SharedBuffer(1024)
        incumbent = CodecBufferSource(WireBuffer(0), shared)
        self.assertIsNotNone(incumbent.get(32))

        message = bytes(range(256))
        packets = self._packets_for(message)
        self.assertTrue(len(packets) > 1)

        gen = codec_v1.read_message(
            self.interface, CodecBufferSource(WireBuffer(0), shared)
        )
        query = gen.send(None)
        # Every continuation report is consumed, and the refusal waits for the last one.
        for packet in packets[:-1]:
            self.assertObjectEqual(query, self.interface.wait_object(io.POLL_READ))
            query = self.interface.mock_read(packet, gen)

        with self.assertRaises(WireError):
            self.interface.mock_read(packets[-1], gen)

        # The wire is back at a message boundary, so the NEXT message reads cleanly rather than
        # being parsed out of the leftovers of this one.
        incumbent.release()
        buffers, _buffer = make_source(256)
        gen = codec_v1.read_message(self.interface, buffers)
        gen.send(None)
        for packet in packets[:-1]:
            self.interface.mock_read(packet, gen)
        with self.assertRaises(StopIteration) as e:
            self.interface.mock_read(packets[-1], gen)
        self.assertEqual(e.value.value.data, message)

    def test_a_message_above_the_hard_bound_is_drained_and_never_allocated(self):
        """`max_message_size` is not `capacity`.

        Above capacity the codec has always fallen back to the heap, which is right for a wallet
        interface and wrong for a permanently listening, unauthenticated one: `msize` is an
        unvalidated uint32, so an advertised length would become an allocation attempt. Above the
        hard bound nothing is allocated at all -- the message is read off the wire and refused.
        """
        small = WireBuffer(512)
        buffers = CodecBufferSource(small, max_size=128)

        message = bytes(range(256))
        packets = self._packets_for(message)

        gen = codec_v1.read_message(self.interface, buffers)
        gen.send(None)
        for packet in packets[:-1]:
            self.interface.mock_read(packet, gen)

        with self.assertRaises(codec_v1.CodecError):
            self.interface.mock_read(packets[-1], gen)

        # Nothing was written anywhere: the message never reached a buffer of its own.
        self.assertEqual(bytes(small.buf), b"\x00" * 512)

    def test_read_many_packets(self):
        message = bytes(range(256))

        header = make_header(mtype=MESSAGE_TYPE, length=len(message))
        # first packet is header + (remaining)data
        # other packets are "?" + 63 bytes of data
        packets = [header + message[:HEADER_PAYLOAD_LENGTH]] + [
            b"?" + chunk
            for chunk in chunks(
                message[HEADER_PAYLOAD_LENGTH:], MockHID.RX_PACKET_LEN - 1
            )
        ]

        buffers, buffer = make_source(256)
        gen = codec_v1.read_message(self.interface, buffers)
        query = gen.send(None)
        for packet in packets[:-1]:
            self.assertObjectEqual(query, self.interface.wait_object(io.POLL_READ))
            query = self.interface.mock_read(packet, gen)

        # last packet will stop
        with self.assertRaises(StopIteration) as e:
            self.interface.mock_read(packets[-1], gen)

        # e.value is StopIteration. e.value.value is the return value of the call
        result = e.value.value
        self.assertEqual(result.type, MESSAGE_TYPE)
        self.assertEqual(result.data, message)

        # message should have been read into the buffer
        self.assertEqual(bytes(buffer), message)

    def test_read_large_message(self):
        message = b"hello world"
        header = make_header(mtype=MESSAGE_TYPE, length=len(message))

        packet = header + message
        # make sure we fit into one packet, to make this easier
        self.assertTrue(len(packet) <= MockHID.RX_PACKET_LEN)

        buffers, buffer = make_source(1)
        self.assertTrue(len(buffer) <= len(packet))

        gen = codec_v1.read_message(self.interface, buffers)
        query = gen.send(None)
        self.assertObjectEqual(query, self.interface.wait_object(io.POLL_READ))
        with self.assertRaises(StopIteration) as e:
            self.interface.mock_read(packet, gen)

        # e.value is StopIteration. e.value.value is the return value of the call
        result = e.value.value
        self.assertEqual(result.type, MESSAGE_TYPE)
        self.assertEqual(result.data, message)

        # read should have allocated its own buffer and not touch ours
        self.assertEqual(bytes(buffer), b"\x00")
        # nothing was borrowed, so there is no lease to give back
        self.assertIsNone(result._buffer_owner)

    def test_write_one_packet(self):
        gen = codec_v1.write_message(self.interface, MESSAGE_TYPE, b"")

        query = gen.send(None)
        self.assertObjectEqual(query, self.interface.wait_object(io.POLL_WRITE))
        with self.assertRaises(StopIteration):
            gen.send(None)

        header = make_header(mtype=MESSAGE_TYPE, length=0)
        expected_message = header + b"\x00" * HEADER_PAYLOAD_LENGTH
        self.assertTrue(self.interface.data == [expected_message])

    def test_write_multiple_packets(self):
        message = bytes(range(256))
        gen = codec_v1.write_message(self.interface, MESSAGE_TYPE, message)

        header = make_header(mtype=MESSAGE_TYPE, length=len(message))
        # first packet is header + (remaining)data
        # other packets are "?" + 63 bytes of data
        packets = [header + message[:HEADER_PAYLOAD_LENGTH]] + [
            b"?" + chunk
            for chunk in chunks(
                message[HEADER_PAYLOAD_LENGTH:], MockHID.RX_PACKET_LEN - 1
            )
        ]

        for _ in packets:
            # we receive as many queries as there are packets
            query = gen.send(None)
            self.assertObjectEqual(query, self.interface.wait_object(io.POLL_WRITE))

        # the first sent None only started the generator. the len(packets)-th None
        # will finish writing and raise StopIteration
        with self.assertRaises(StopIteration):
            gen.send(None)

        # packets must be identical up to the last one
        self.assertListEqual(packets[:-1], self.interface.data[:-1])
        # last packet must be identical up to message length. remaining bytes in
        # the 64-byte packets are garbage -- in particular, it's the bytes of the
        # previous packet
        last_packet = packets[-1] + packets[-2][len(packets[-1]) :]
        self.assertEqual(last_packet, self.interface.data[-1])

    def test_roundtrip(self):
        message = bytes(range(256))
        gen = codec_v1.write_message(self.interface, MESSAGE_TYPE, message)

        # exhaust the iterator:
        # (XXX we can only do this because the iterator is only accepting None and returns None)
        for query in gen:
            self.assertObjectEqual(query, self.interface.wait_object(io.POLL_WRITE))

        gen = codec_v1.read_message(self.interface, private_source(1024))
        query = gen.send(None)
        for packet in self.interface.data[:-1]:
            self.assertObjectEqual(query, self.interface.wait_object(io.POLL_READ))
            query = self.interface.mock_read(packet, gen)

        with self.assertRaises(StopIteration) as e:
            self.interface.mock_read(self.interface.data[-1], gen)

        result = e.value.value
        self.assertEqual(result.type, MESSAGE_TYPE)
        self.assertEqual(result.data, message)

    def test_read_huge_packet(self):
        PACKET_COUNT = 100_000
        # message that takes up 100 000 USB packets
        message_size = (PACKET_COUNT - 1) * 63 + HEADER_PAYLOAD_LENGTH
        # ensure that a message this big won't fit into memory
        self.assertRaises(MemoryError, bytearray, message_size)

        header = make_header(mtype=MESSAGE_TYPE, length=message_size)
        packet = header + b"\x00" * HEADER_PAYLOAD_LENGTH

        gen = codec_v1.read_message(self.interface, private_source(65536))

        query = gen.send(None)
        for _ in range(PACKET_COUNT - 1):
            self.assertObjectEqual(query, self.interface.wait_object(io.POLL_READ))
            query = self.interface.mock_read(packet, gen)

        with self.assertRaises(codec_v1.CodecError) as e:
            self.interface.mock_read(packet, gen)

        self.assertEqual(e.value.args[0], "Message too large")


class TestCodecBufferSource(unittest.TestCase):
    """The four tiers a codec message can land in, and which of them carry a lease.

    The pool is what lets the WARD service interface talk to its daemon in the middle of a wallet
    workflow. What sits above it -- the heap, and draining a message too big for even that -- is
    older than the pool and must not be lost with it.
    """

    def test_a_small_message_never_borrows(self):
        shared = SharedBuffer(1024)
        source = CodecBufferSource(WireBuffer(64), shared)

        self.assertIsNotNone(source.get(64))
        self.assertFalse(source.holds_shared())
        self.assertIsNone(shared.holder)

    def test_a_larger_message_borrows_and_gives_back(self):
        shared = SharedBuffer(1024)
        source = CodecBufferSource(WireBuffer(64), shared)

        buf = source.get(65)
        self.assertEqual(len(buf), 65)
        self.assertTrue(source.holds_shared())

        source.release()
        self.assertFalse(source.holds_shared())
        self.assertIsNone(shared.holder)

    def test_the_second_claimant_is_refused_rather_than_given_the_same_memory(self):
        shared = SharedBuffer(1024)
        first = CodecBufferSource(WireBuffer(0), shared)
        second = CodecBufferSource(WireBuffer(0), shared)

        self.assertIsNotNone(first.get(128))
        self.assertIsNone(second.get(128))

        first.release()
        self.assertIsNotNone(second.get(128))

    def test_capacity_is_the_shared_size_when_there_is_one(self):
        self.assertEqual(
            CodecBufferSource(WireBuffer(64), SharedBuffer(1024)).capacity(), 1024
        )

    def test_a_private_source_borrows_nothing(self):
        source = private_source(64)

        self.assertEqual(source.capacity(), 64)
        self.assertIsNotNone(source.get(64))
        self.assertFalse(source.holds_shared())
        # never refused, which is why debuglink uses one
        self.assertIsNotNone(private_source(64).get(64))

    def test_release_is_idempotent_and_safe_without_a_lease(self):
        source = CodecBufferSource(WireBuffer(64), SharedBuffer(1024))
        source.release()
        source.get(128)
        source.release()
        source.release()
        self.assertFalse(source.holds_shared())


if __name__ == "__main__":
    unittest.main()
