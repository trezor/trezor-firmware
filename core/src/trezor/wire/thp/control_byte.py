from trezor.wire.thp import ThpError
from trezor.wire.thp.thp_messages import (
    ACK_MASK,
    ACK_MESSAGE,
    CONTINUATION_PACKET,
    CONTINUATION_PACKET_MASK,
    DATA_MASK,
    ENCRYPTED_TRANSPORT,
    HANDSHAKE_COMP_REQ,
    HANDSHAKE_INIT_REQ,
)


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
    return ctrl_byte & ACK_MASK == ACK_MESSAGE


def is_continuation(ctrl_byte: int) -> bool:
    return ctrl_byte & CONTINUATION_PACKET_MASK == CONTINUATION_PACKET


def is_encrypted_transport(ctrl_byte: int) -> bool:
    return ctrl_byte & DATA_MASK == ENCRYPTED_TRANSPORT


def is_handshake_init_req(ctrl_byte: int) -> bool:
    return ctrl_byte & DATA_MASK == HANDSHAKE_INIT_REQ


def is_handshake_comp_req(ctrl_byte: int) -> bool:
    return ctrl_byte & DATA_MASK == HANDSHAKE_COMP_REQ
