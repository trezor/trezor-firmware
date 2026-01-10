# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

from typing import Optional

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


def add_seq_bit_to_ctrl_byte(ctrl_byte: int, seq_bit: int) -> int:
    if seq_bit == 0:
        return ctrl_byte & 0xEF
    if seq_bit == 1:
        return ctrl_byte | 0x10
    raise Exception("Unexpected sequence bit")


def add_ack_bit_to_ctrl_byte(ctrl_byte: int, ack_bit: int) -> int:
    if ack_bit == 0:
        return ctrl_byte & 0xF7
    if ack_bit == 1:
        return ctrl_byte | 0x08
    raise Exception("Unexpected acknowledgement bit")


def get_ack_bit(ctrl_byte: int) -> Optional[int]:
    if ctrl_byte & 0xE0 and not is_ack(ctrl_byte):
        # not all message types contain ACK bit
        return None

    return (ctrl_byte & 0x08) >> 3


def get_seq_bit(ctrl_byte: int) -> Optional[int]:
    if ctrl_byte & 0xE0:
        # not all message types contain SEQ bit
        return None

    return (ctrl_byte & 0x10) >> 4


def is_ack(ctrl_byte: int) -> bool:
    return ctrl_byte & ACK_MASK == ACK_MESSAGE


def is_error(ctrl_byte: int) -> bool:
    return ctrl_byte == _ERROR


def is_continuation(ctrl_byte: int) -> bool:
    return ctrl_byte & CONTINUATION_PACKET_MASK == CONTINUATION_PACKET


def is_encrypted_transport(ctrl_byte: int) -> bool:
    return ctrl_byte & DATA_MASK == ENCRYPTED_TRANSPORT


def is_handshake_init_req(ctrl_byte: int) -> bool:
    return ctrl_byte & DATA_MASK == HANDSHAKE_INIT_REQ


def is_handshake_comp_req(ctrl_byte: int) -> bool:
    return ctrl_byte & DATA_MASK == HANDSHAKE_COMP_REQ
