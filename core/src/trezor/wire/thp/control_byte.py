from micropython import const

from . import (
    ACK_MESSAGE,
    CONTINUATION_PACKET,
    ENCRYPTED,
    HANDSHAKE_COMP_REQ,
    HANDSHAKE_INIT_REQ,
)

_CONTINUATION_PACKET_MASK = const(0x80)
_ACK_MASK = const(0xF7)
_DATA_MASK = const(0xE7)


def add_seq_bit_to_ctrl_byte(ctrl_byte: int, seq_bit: int) -> int:
    assert seq_bit in (0, 1)
    if seq_bit:
        return ctrl_byte | 0x10
    else:
        return ctrl_byte & 0xEF


def add_ack_bit_to_ctrl_byte(ctrl_byte: int, ack_bit: int) -> int:
    assert ack_bit in (0, 1)
    if ack_bit:
        return ctrl_byte | 0x08
    else:
        return ctrl_byte & 0xF7


def get_ack_bit(ctrl_byte: int) -> int:
    return (ctrl_byte & 0x08) >> 3


def get_seq_bit(ctrl_byte: int) -> int:
    return (ctrl_byte & 0x10) >> 4


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
