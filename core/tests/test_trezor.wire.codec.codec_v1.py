# flake8: noqa: F403,F405
from common import *  # isort:skip

import ustruct

from trezor import io
from trezor.loop import wait
from trezor.utils import chunks
from trezor.wire.codec import codec_v1
from trezor.wire.protocol_common import WireError


class MockHID:

    TX_PACKET_LEN = 64
    RX_PACKET_LEN = 64

    def __init__(self, num):
        self.num = num
        self.data = []
        self.packet = None

    def pad_packet(self, data):
        if len(data) > self.RX_PACKET_LEN:
            raise Exception("Too long packet")
        padding_length = self.RX_PACKET_LEN - len(data)
        return data + b"\x00" * padding_length

    def iface_num(self):
        return self.num

    def write(self, msg):
        self.data.append(bytearray(msg))
        return len(msg)

    def mock_read(self, packet, gen):
        self.packet = self.pad_packet(packet)
        return gen.send(self.RX_PACKET_LEN)

    def read(self, buffer, offset=0):
        if self.packet is None:
            raise Exception("No packet to read")

        if offset > len(buffer):
            raise Exception("Offset out of bounds")

        buffer_space = len(buffer) - offset

        if len(self.packet) > buffer_space:
            raise Exception("Buffer too small")
        else:
            end = offset + len(self.packet)
            buffer[offset:end] = self.packet
            read = len(self.packet)
            self.packet = None
            return read

    def wait_object(self, mode):
        return wait(mode | self.num)


MESSAGE_TYPE = 0x4242

HEADER_PAYLOAD_LENGTH = MockHID.RX_PACKET_LEN - 3 - ustruct.calcsize(">HL")


def make_header(mtype, length):
    return b"?##" + ustruct.pack(">HL", mtype, length)


class TestWireCodecV1(unittest.TestCase):
    def setUp(self):
        self.interface = MockHID(0xDEADBEEF)

    def test_read_one_packet(self):
        # zero length message - just a header
        message_packet = make_header(mtype=MESSAGE_TYPE, length=0)
        buffer = bytearray(64)

        gen = codec_v1.read_message(self.interface, lambda: buffer)

        query = gen.send(None)
        self.assertObjectEqual(query, self.interface.wait_object(io.POLL_READ))

        with self.assertRaises(StopIteration) as e:
            self.interface.mock_read(message_packet, gen)

        # e.value is StopIteration. e.value.value is the return value of the call
        result = e.value.value
        self.assertEqual(result.type, MESSAGE_TYPE)
        self.assertEqual(result.data, b"")

        # message should have been read into the buffer
        self.assertEqual(buffer, b"\x00" * 64)

    def test_read_no_buffer(self):
        # zero length message - just a header
        message_packet = make_header(mtype=MESSAGE_TYPE, length=0)
        gen = codec_v1.read_message(self.interface, lambda: None)

        query = gen.send(None)
        self.assertObjectEqual(query, self.interface.wait_object(io.POLL_READ))

        with self.assertRaises(WireError):
            self.interface.mock_read(message_packet, gen)

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

        buffer = bytearray(256)
        gen = codec_v1.read_message(self.interface, lambda: buffer)
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
        self.assertEqual(buffer, message)

    def test_read_large_message(self):
        message = b"hello world"
        header = make_header(mtype=MESSAGE_TYPE, length=len(message))

        packet = header + message
        # make sure we fit into one packet, to make this easier
        self.assertTrue(len(packet) <= MockHID.RX_PACKET_LEN)

        buffer = bytearray(1)
        self.assertTrue(len(buffer) <= len(packet))

        gen = codec_v1.read_message(self.interface, lambda: buffer)
        query = gen.send(None)
        self.assertObjectEqual(query, self.interface.wait_object(io.POLL_READ))
        with self.assertRaises(StopIteration) as e:
            self.interface.mock_read(packet, gen)

        # e.value is StopIteration. e.value.value is the return value of the call
        result = e.value.value
        self.assertEqual(result.type, MESSAGE_TYPE)
        self.assertEqual(result.data, message)

        # read should have allocated its own buffer and not touch ours
        self.assertEqual(buffer, b"\x00")

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

        buffer = bytearray(1024)
        gen = codec_v1.read_message(self.interface, lambda: buffer)
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

        buffer = bytearray(65536)
        gen = codec_v1.read_message(self.interface, lambda: buffer)

        query = gen.send(None)
        for _ in range(PACKET_COUNT - 1):
            self.assertObjectEqual(query, self.interface.wait_object(io.POLL_READ))
            query = self.interface.mock_read(packet, gen)

        with self.assertRaises(codec_v1.CodecError) as e:
            self.interface.mock_read(packet, gen)

        self.assertEqual(e.value.args[0], "Message too large")


if __name__ == "__main__":
    unittest.main()
