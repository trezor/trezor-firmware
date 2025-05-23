import struct

CODEC_V1 = 0x3F
CONTINUATION_PACKET = 0x80
HANDSHAKE_INIT_REQ = 0x00
HANDSHAKE_INIT_RES = 0x01
HANDSHAKE_COMP_REQ = 0x02
HANDSHAKE_COMP_RES = 0x03
ENCRYPTED_TRANSPORT = 0x04

CONTINUATION_PACKET_MASK = 0x80
ACK_MASK = 0xF7
DATA_MASK = 0xE7

ACK_MESSAGE = 0x20
_ERROR = 0x42
CHANNEL_ALLOCATION_REQ = 0x40
_CHANNEL_ALLOCATION_RES = 0x41

TREZOR_STATE_UNPAIRED = b"\x00"
TREZOR_STATE_PAIRED = b"\x01"

BROADCAST_CHANNEL_ID = 0xFFFF


class MessageHeader:
    format_str_init = ">BHH"
    format_str_cont = ">BH"

    def __init__(self, ctrl_byte: int, cid: int, length: int) -> None:
        self.ctrl_byte = ctrl_byte
        self.cid = cid
        self.data_length = length

    def to_bytes_init(self) -> bytes:
        return struct.pack(
            self.format_str_init, self.ctrl_byte, self.cid, self.data_length
        )

    def to_bytes_cont(self) -> bytes:
        return struct.pack(self.format_str_cont, CONTINUATION_PACKET, self.cid)

    def pack_to_init_buffer(self, buffer: bytearray, buffer_offset: int = 0) -> None:
        struct.pack_into(
            self.format_str_init,
            buffer,
            buffer_offset,
            self.ctrl_byte,
            self.cid,
            self.data_length,
        )

    def pack_to_cont_buffer(self, buffer: bytearray, buffer_offset: int = 0) -> None:
        struct.pack_into(
            self.format_str_cont, buffer, buffer_offset, CONTINUATION_PACKET, self.cid
        )

    def is_ack(self) -> bool:
        return self.ctrl_byte & ACK_MASK == ACK_MESSAGE

    def is_channel_allocation_response(self):
        return (
            self.cid == BROADCAST_CHANNEL_ID
            and self.ctrl_byte == _CHANNEL_ALLOCATION_RES
        )

    def is_handshake_init_response(self) -> bool:
        return self.ctrl_byte & DATA_MASK == HANDSHAKE_INIT_RES

    def is_handshake_comp_response(self) -> bool:
        return self.ctrl_byte & DATA_MASK == HANDSHAKE_COMP_RES

    def is_encrypted_transport(self) -> bool:
        return self.ctrl_byte & DATA_MASK == ENCRYPTED_TRANSPORT

    @classmethod
    def get_error_header(cls, cid: int, length: int):
        return cls(_ERROR, cid, length)

    @classmethod
    def get_channel_allocation_request_header(cls, length: int):
        return cls(CHANNEL_ALLOCATION_REQ, BROADCAST_CHANNEL_ID, length)
