from micropython import const

from . import (
    ACK_MESSAGE,
    CONTINUATION_PACKET,
    ENCRYPTED,
    HANDSHAKE_COMP_REQ,
    HANDSHAKE_INIT_REQ,
    ThpError,
)

_CONTINUATION_PACKET_MASK = const(0x80)
_ACK_MASK = const(0xF7)
_DATA_MASK = const(0xE7)


def add_seq_bit_to_ctrl_byte(ctrl_byte: int, seq_bit: int) -> int:
    if seq_bit == 0:
        return ctrl_byte & 0xEF
    if seq_bit == 1:
        return ctrl_byte | 0x10
    raise ThpError("Unexpected sequence bit")


def add_ack_bit_to_ctrl_byte(ctrl_byte: int, ack_bit: int) -> int:
    if ack_bit == 0:
        return ctrl_byte & 0xF7
    if ack_bit == 1:
        return ctrl_byte | 0x08
    raise ThpError("Unexpected acknowledgement bit")


def is_ack(ctrl_byte: int) -> bool:
    return ctrl_byte & _ACK_MASK == ACK_MESSAGE


def is_continuation(ctrl_byte: int) -> bool:
    return ctrl_byte & _CONTINUATION_PACKET_MASK == CONTINUATION_PACKET


def is_encrypted_transport(ctrl_byte: int) -> bool:
    return ctrl_byte & _DATA_MASK == ENCRYPTED


def is_handshake_init_req(ctrl_byte: int) -> bool:
    return ctrl_byte & _DATA_MASK == HANDSHAKE_INIT_REQ


def is_handshake_comp_req(ctrl_byte: int) -> bool:
    return ctrl_byte & _DATA_MASK == HANDSHAKE_COMP_REQ
