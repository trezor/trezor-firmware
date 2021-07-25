from common import *

from trezor import protobuf
from trezor.messages import WebAuthnCredential, EosAsset, Failure, SignMessage


def load_uvarint32(data: bytes) -> int:
    # use known uint32 field in an all-optional message
    buffer = bytearray(len(data) + 1)
    buffer[1:] = data
    buffer[0] = (1 << 3) | 0  # field number 1, wire type 0
    msg = protobuf.decode(buffer, WebAuthnCredential, False)
    return msg.index


def load_uvarint64(data: bytes) -> int:
    # use known uint64 field in an all-optional message
    buffer = bytearray(len(data) + 1)
    buffer[1:] = data
    buffer[0] = (2 << 3) | 0  # field number 1, wire type 0
    msg = protobuf.decode(buffer, EosAsset, False)
    return msg.symbol


def dump_uvarint32(value: int) -> bytearray:
    # use known uint32 field in an all-optional message
    msg = WebAuthnCredential(index=value)
    length = protobuf.encoded_length(msg)
    buffer = bytearray(length)
    protobuf.encode(buffer, msg)
    assert buffer[0] == (1 << 3) | 0  # field number 1, wire type 0
    return buffer[1:]


def dump_uvarint64(value: int) -> bytearray:
    # use known uint64 field in an all-optional message
    msg = EosAsset(symbol=value)
    length = protobuf.encoded_length(msg)
    buffer = bytearray(length)
    protobuf.encode(buffer, msg)
    assert buffer[0] == (2 << 3) | 0  # field number 2, wire type 0
    return buffer[1:]


def dump_message(msg: protobuf.MessageType) -> bytearray:
    length = protobuf.encoded_length(msg)
    buffer = bytearray(length)
    protobuf.encode(buffer, msg)
    return buffer


def load_message(msg_type: Type[protobuf.MessageType], buffer: bytes) -> protobuf.MessageType:
    return protobuf.decode(buffer, msg_type, False)


class TestProtobuf(unittest.TestCase):
    def test_dump_uvarint(self):
        for dump_uvarint in (dump_uvarint32, dump_uvarint64):
            self.assertEqual(dump_uvarint(0), b"\x00")
            self.assertEqual(dump_uvarint(1), b"\x01")
            self.assertEqual(dump_uvarint(0xFF), b"\xff\x01")
            self.assertEqual(dump_uvarint(123456), b"\xc0\xc4\x07")
            with self.assertRaises(ValueError):
                dump_uvarint(-1)

    def test_load_uvarint(self):
        for load_uvarint in (load_uvarint32, load_uvarint64):
            self.assertEqual(load_uvarint(b"\x00"), 0)
            self.assertEqual(load_uvarint(b"\x01"), 1)
            self.assertEqual(load_uvarint(b"\xff\x01"), 0xFF)
            self.assertEqual(load_uvarint(b"\xc0\xc4\x07"), 123456)

    def test_validate_enum(self):
        # ok message:
        msg = Failure(code=7)
        msg_encoded = dump_message(msg)
        nmsg = load_message(Failure, msg_encoded)

        self.assertEqual(msg.code, nmsg.code)

        # bad enum value:
        msg = Failure(code=1000)
        msg_encoded = dump_message(msg)
        with self.assertRaises(ValueError):
            load_message(Failure, msg_encoded)

    def test_required(self):
        msg = SignMessage(message=b"hello", coin_name="foo", script_type=1)
        msg_encoded = dump_message(msg)
        nmsg = load_message(SignMessage, msg_encoded)

        self.assertEqual(nmsg.message, b"hello")
        self.assertEqual(nmsg.coin_name, "foo")
        self.assertEqual(nmsg.script_type, 1)

        # try a message without the required_field
        msg = SignMessage(message=None)
        # encoding always succeeds
        msg_encoded = dump_message(msg)
        with self.assertRaises(ValueError):
            load_message(SignMessage, msg_encoded)

        # try a message without the default field
        msg = SignMessage(message=b"hello")
        msg.coin_name = None
        msg_encoded = dump_message(msg)
        nmsg = load_message(SignMessage, msg_encoded)

        self.assertEqual(nmsg.message, b"hello")
        self.assertEqual(nmsg.coin_name, "Bitcoin")



if __name__ == "__main__":
    unittest.main()
