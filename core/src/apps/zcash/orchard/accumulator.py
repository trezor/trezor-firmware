import gc
from typing import TYPE_CHECKING

from trezor import protobuf
from trezor.crypto import aes
from trezor.crypto.hashlib import sha256
from trezor.wire import ProcessError

if TYPE_CHECKING:
    from trezor.protobuf import MessageType

    pass

EMPTY = 32 * b"\x00"


def xor(x: bytes, y: bytes) -> bytes:
    return bytes([a ^ b for a, b in zip(x, y)])


class MessageAccumulator:
    def __init__(self, key: bytes) -> None:
        self.key = key
        self.state = EMPTY

    def xor_message(self, msg: MessageType, index: int) -> None:
        gc.collect()
        cipher = aes(aes.ECB, self.key)

        # compute mask
        assert msg.MESSAGE_WIRE_TYPE is not None
        mask_preimage = bytearray(32)
        mask_preimage[0:2] = msg.MESSAGE_WIRE_TYPE.to_bytes(2, "big")
        mask_preimage[2:6] = index.to_bytes(4, "little")
        mask = cipher.encrypt(mask_preimage)

        msg_digest = sha256(protobuf.dump_message_buffer(msg)).digest()
        prp_input = xor(mask, msg_digest)
        prp_output = cipher.encrypt(prp_input)
        self.state = xor(self.state, prp_output)
        gc.collect()

    def check(self) -> None:
        if self.state != EMPTY:
            raise ProcessError("Message changed.")
