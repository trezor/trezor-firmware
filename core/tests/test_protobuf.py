from common import *

import protobuf
from trezor.utils import BufferReader, BufferWriter


class Message(protobuf.MessageType):
    def __init__(self, sint_field: int = 0, enum_field: int = 0) -> None:
        self.sint_field = sint_field
        self.enum_field = enum_field

    @classmethod
    def get_fields(cls):
        return {
            1: ("sint_field", protobuf.SVarintType, 0),
            2: ("enum_field", protobuf.EnumType("t", (0, 5, 25)), 0),
        }


class MessageWithRequiredAndDefault(protobuf.MessageType):
    def __init__(self, required_field, default_field) -> None:
        self.required_field = required_field
        self.default_field = default_field

    @classmethod
    def get_fields(cls):
        return {
            1: ("required_field", protobuf.UVarintType, protobuf.FLAG_REQUIRED),
            2: ("default_field", protobuf.SVarintType, -1),
        }


def load_uvarint(data: bytes) -> int:
    reader = BufferReader(data)
    return protobuf.load_uvarint(reader)


def dump_uvarint(value: int) -> bytearray:
    w = bytearray()
    protobuf.dump_uvarint(w.extend, value)
    return w


def dump_message(msg: protobuf.MessageType) -> bytearray:
    length = protobuf.count_message(msg)
    buffer = bytearray(length)
    protobuf.dump_message(BufferWriter(buffer), msg)
    return buffer


def load_message(msg_type, buffer: bytearray) -> protobuf.MessageType:
    return protobuf.load_message(BufferReader(buffer), msg_type)


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
            protobuf.uint_to_sint(protobuf.sint_to_uint(-(2 ** 32))), -(2 ** 32)
        )

    def test_validate_enum(self):
        # ok message:
        msg = Message(-42, 5)
        msg_encoded = dump_message(msg)
        nmsg = load_message(Message, msg_encoded)

        self.assertEqual(msg.sint_field, nmsg.sint_field)
        self.assertEqual(msg.enum_field, nmsg.enum_field)

        # bad enum value:
        msg = Message(-42, 42)
        msg_encoded = dump_message(msg)
        with self.assertRaises(TypeError):
            load_message(Message, msg_encoded)

    def test_required(self):
        msg = MessageWithRequiredAndDefault(required_field=1, default_field=2)
        msg_encoded = dump_message(msg)
        nmsg = load_message(MessageWithRequiredAndDefault, msg_encoded)

        self.assertEqual(nmsg.required_field, 1)
        self.assertEqual(nmsg.default_field, 2)

        # try a message without the required_field
        msg = MessageWithRequiredAndDefault(required_field=None, default_field=2)
        # encoding always succeeds
        msg_encoded = dump_message(msg)
        with self.assertRaises(ValueError):
            load_message(MessageWithRequiredAndDefault, msg_encoded)

        # try a message without the default field
        msg = MessageWithRequiredAndDefault(required_field=1, default_field=None)
        msg_encoded = dump_message(msg)
        nmsg = load_message(MessageWithRequiredAndDefault, msg_encoded)

        self.assertEqual(nmsg.required_field, 1)
        self.assertEqual(nmsg.default_field, -1)



if __name__ == "__main__":
    unittest.main()
