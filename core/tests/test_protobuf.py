from common import *

import protobuf

if False:
    from typing import Awaitable, Dict


class Message(protobuf.MessageType):
    def __init__(self, uint_field: int = 0, enum_field: int = 0) -> None:
        self.sint_field = uint_field
        self.enum_field = enum_field

    @classmethod
    def get_fields(cls) -> Dict:
        return {
            1: ("sint_field", protobuf.SVarintType, 0),
            2: ("enum_field", protobuf.EnumType("t", (0, 5, 25)), 0),
        }


class ByteReader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.pos = 0

    async def areadinto(self, buf: bytearray) -> int:
        remaining = len(self.data) - self.pos
        limit = len(buf)
        if remaining < limit:
            raise EOFError

        buf[:] = self.data[self.pos : self.pos + limit]
        self.pos += limit
        return limit


class ByteArrayWriter:
    def __init__(self) -> None:
        self.buf = bytearray(0)

    async def awrite(self, buf: bytes) -> int:
        self.buf.extend(buf)
        return len(buf)


def run_until_complete(task: Awaitable) -> Any:
    value = None
    while True:
        try:
            result = task.send(value)
        except StopIteration as e:
            return e.value

        if result:
            value = run_until_complete(result)
        else:
            value = None


def load_uvarint(data: bytes) -> int:
    reader = ByteReader(data)
    return run_until_complete(protobuf.load_uvarint(reader))


def dump_uvarint(value: int) -> bytearray:
    writer = ByteArrayWriter()
    run_until_complete(protobuf.dump_uvarint(writer, value))
    return writer.buf


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
        writer = ByteArrayWriter()
        run_until_complete(protobuf.dump_message(writer, msg))
        reader = ByteReader(bytes(writer.buf))
        nmsg = run_until_complete(protobuf.load_message(reader, Message))

        self.assertEqual(msg.sint_field, nmsg.sint_field)
        self.assertEqual(msg.enum_field, nmsg.enum_field)

        # bad enum value:
        msg = Message(-42, 42)
        writer = ByteArrayWriter()
        run_until_complete(protobuf.dump_message(writer, msg))
        reader = ByteReader(bytes(writer.buf))
        with self.assertRaises(TypeError):
            run_until_complete(protobuf.load_message(reader, Message))


if __name__ == "__main__":
    unittest.main()
