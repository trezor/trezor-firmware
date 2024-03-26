import ustruct  # pyright:ignore[reportMissingModuleSource]
from micropython import const

from storage.cache_thp import BROADCAST_CHANNEL_ID

from ..protocol_common import Message

CODEC_V1 = 0x3F
CONTINUATION_PACKET = 0x80
ENCRYPTED_TRANSPORT = 0x02
HANDSHAKE_INIT = 0x00
ACK_MESSAGE = 0x20
_ERROR = 0x41
_CHANNEL_ALLOCATION_RES = 0x40
INIT_DATA_OFFSET = const(5)
CONT_DATA_OFFSET = const(3)


class InitHeader:
    format_str = ">BHH"

    def __init__(self, ctrl_byte, cid, length) -> None:
        self.ctrl_byte = ctrl_byte
        self.cid = cid
        self.length = length

    def to_bytes(self) -> bytes:
        return ustruct.pack(
            InitHeader.format_str, self.ctrl_byte, self.cid, self.length
        )

    def pack_to_buffer(self, buffer, buffer_offset=0) -> None:
        ustruct.pack_into(
            InitHeader.format_str,
            buffer,
            buffer_offset,
            self.ctrl_byte,
            self.cid,
            self.length,
        )

    def pack_to_cont_buffer(self, buffer, buffer_offset=0) -> None:
        ustruct.pack_into(">BH", buffer, buffer_offset, CONTINUATION_PACKET, self.cid)

    @classmethod
    def get_error_header(cls, cid, length):
        return cls(_ERROR, cid, length)

    @classmethod
    def get_channel_allocation_response_header(cls, length):
        return cls(_CHANNEL_ALLOCATION_RES, BROADCAST_CHANNEL_ID, length)


class InterruptingInitPacket:
    def __init__(self, report: bytes) -> None:
        self.initReport = report


_ENCODED_PROTOBUF_DEVICE_PROPERTIES = (
    b"\x0a\x04\x54\x33\x57\x31\x10\x05\x18\x00\x20\x01\x28\x01\x28\x02"
)

_ERROR_UNALLOCATED_SESSION = (
    b"\x55\x4e\x41\x4c\x4c\x4f\x43\x41\x54\x45\x44\x5f\x53\x45\x53\x53\x49\x4f\x4e"
)


def get_device_properties() -> Message:
    return Message(_ENCODED_PROTOBUF_DEVICE_PROPERTIES)


def get_channel_allocation_response(nonce: bytes, new_cid: bytes) -> bytes:
    props_msg = get_device_properties()
    return nonce + new_cid + props_msg.to_bytes()


def get_error_unallocated_channel() -> bytes:
    return _ERROR_UNALLOCATED_SESSION
