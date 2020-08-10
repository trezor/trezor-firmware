from common import *

import protobuf
from trezor.utils import BufferReader, BufferWriter


class Message(protobuf.MessageType):
    def __init__(self, uint_field: int = 0, enum_field: int = 0) -> None:
        self.sint_field = uint_field
        self.enum_field = enum_field

    @classmethod
    def get_fields(cls):
        return {
            1: ("sint_field", protobuf.SVarintType, 0),
            2: ("enum_field", protobuf.EnumType("t", (0, 5, 25)), 0),
        }


def load_uvarint(data: bytes) -> int:
    reader = BufferReader(data)
    return protobuf.load_uvarint(reader)


def dump_uvarint(value: int) -> bytearray:
    writer = BufferWriter(bytearray(16))
    protobuf.dump_uvarint(writer, value)
    return memoryview(writer.buffer)[:writer.offset]


class TestProtobuf(unittest.TestCase):
    def test_dump_uvarint(self):
        self.assertEqual(dump_uvarint(0), b"\x00")
        self.assertEqual(dump_uvarint(1), b"\x01")
        self.assertEqual(dump_uvarint(0xFF), b"\xff\x01")
        self.assertEqual(dump_uvarint(123456), b"\xc0\xc4\x07")
        with self.assertRaises(ValueError):
            dump_uvarint(-1)

    def test_load_uvarint(self):
        self.assertEqual(load_uvarint(b"\x00"), 0)
        self.assertEqual(load_uvarint(b"\x01"), 1)
        self.assertEqual(load_uvarint(b"\xff\x01"), 0xFF)
        self.assertEqual(load_uvarint(b"\xc0\xc4\x07"), 123456)

    def test_sint_uint(self):
        self.assertEqual(protobuf.uint_to_sint(0), 0)
        self.assertEqual(protobuf.sint_to_uint(0), 0)

        self.assertEqual(protobuf.sint_to_uint(-1), 1)
        self.assertEqual(protobuf.sint_to_uint(1), 2)

        self.assertEqual(protobuf.uint_to_sint(1), -1)
        self.assertEqual(protobuf.uint_to_sint(2), 1)

        # roundtrip:
        self.assertEqual(
            protobuf.uint_to_sint(protobuf.sint_to_uint(1234567891011)), 1234567891011
        )
        self.assertEqual(
            protobuf.uint_to_sint(protobuf.sint_to_uint(-2 ** 32)), -2 ** 32
        )

    def test_validate_enum(self):
        # ok message:
        msg = Message(-42, 5)
        length = protobuf.count_message(msg)
        buffer_writer = BufferWriter(bytearray(length))
        protobuf.dump_message(buffer_writer, msg)

        buffer_reader = BufferReader(buffer_writer.buffer)
        nmsg = protobuf.load_message(buffer_reader, Message)

        self.assertEqual(msg.sint_field, nmsg.sint_field)
        self.assertEqual(msg.enum_field, nmsg.enum_field)

        # bad enum value:
        buffer_writer.seek(0)
        msg = Message(-42, 42)
        # XXX this assumes the message will have equal size
        protobuf.dump_message(buffer_writer, msg)
        buffer_reader.seek(0)
        with self.assertRaises(TypeError):
            protobuf.load_message(buffer_reader, Message)


if __name__ == "__main__":
    unittest.main()
