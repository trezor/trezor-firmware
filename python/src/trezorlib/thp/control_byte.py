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

from __future__ import annotations

CONTINUATION_BIT = 0b1000_0000

# data packets
DATA_MASK = 0xE7
HANDSHAKE_INIT_REQ = 0x00
HANDSHAKE_INIT_RES = 0x01
HANDSHAKE_COMP_REQ = 0x02
HANDSHAKE_COMP_RES = 0x03
ENCRYPTED_TRANSPORT = 0x04
DATA_SEQ_BIT = 0b0001_0000
DATA_ACK_SEQ_BIT = 0b0000_1000

DATA_DETECT_BASE = 0b0000_0000
DATA_DETECT_MASK = 0b1110_0000

# ack packets
ACK_MASK = 0b1111_0111
ACK_BASE = 0b0010_0000
ACK_SEQ_BIT = 0b0000_1000

# special values
CODEC_V1 = 0x3F
CHANNEL_ALLOCATION_REQ = 0x40
CHANNEL_ALLOCATION_RES = 0x41
ERROR = 0x42
PING = 0x43
PONG = 0x44


HANDSHAKE_SEQ_BITS = {
    HANDSHAKE_INIT_REQ: False,
    HANDSHAKE_INIT_RES: False,
    HANDSHAKE_COMP_REQ: True,
    HANDSHAKE_COMP_RES: True,
}


FIXED_NAMES = {
    CODEC_V1: "CODEC_V1",
    CHANNEL_ALLOCATION_REQ: "CHANNEL_ALLOCATION_REQ",
    CHANNEL_ALLOCATION_RES: "CHANNEL_ALLOCATION_RES",
    ERROR: "ERROR",
    PING: "PING",
    PONG: "PONG",
}

DATA_NAMES = {
    HANDSHAKE_INIT_REQ: "HANDSHAKE_INIT_REQ",
    HANDSHAKE_INIT_RES: "HANDSHAKE_INIT_RES",
    HANDSHAKE_COMP_REQ: "HANDSHAKE_COMP_REQ",
    HANDSHAKE_COMP_RES: "HANDSHAKE_COMP_RES",
    ENCRYPTED_TRANSPORT: "ENCRYPTED_TRANSPORT",
}


def to_string(ctrl_byte: int) -> str:
    hex = f"0x{ctrl_byte:02x}"
    if is_continuation(ctrl_byte):
        return f"{hex} (CONTINUATION)"
    if ctrl_byte in FIXED_NAMES:
        return f"{hex} ({FIXED_NAMES[ctrl_byte]})"
    if is_ack(ctrl_byte):
        ack_bit = bool(ctrl_byte & ACK_SEQ_BIT)
        return f"{hex} (ACK{int(ack_bit)})"
    if ctrl_byte & DATA_MASK in DATA_NAMES:
        seq_bit = int(get_seq_bit(ctrl_byte) or 0)
        ack_bit = int(bool(ctrl_byte & DATA_ACK_SEQ_BIT) or 0)
        return f"{hex} ({DATA_NAMES[ctrl_byte & DATA_MASK]} seq{seq_bit} ack{ack_bit})"
    return f"{hex} (reserved)"


def set_seq_bit(ctrl_byte: int, seq_bit: bool) -> int:
    if not is_data(ctrl_byte):
        return ctrl_byte
    return ctrl_byte | (DATA_SEQ_BIT * seq_bit)


def add_ack_bit_to_ctrl_byte(ctrl_byte: int, ack_bit: int) -> int:
    return ctrl_byte | (DATA_ACK_SEQ_BIT * ack_bit)


def get_seq_bit(ctrl_byte: int) -> bool | None:
    if ctrl_byte in HANDSHAKE_SEQ_BITS:
        return HANDSHAKE_SEQ_BITS[ctrl_byte]
    if not is_data(ctrl_byte):
        # not all message types contain SEQ bit
        return None
    return bool(ctrl_byte & DATA_SEQ_BIT)


def get_ack_bit(ctrl_byte: int) -> bool | None:
    if not is_ack(ctrl_byte):
        return None
    return bool(ctrl_byte & ACK_SEQ_BIT)


def make_ack(ack_bit: bool) -> int:
    return ACK_BASE | (ACK_SEQ_BIT * ack_bit)


def make_ack_for(ctrl_byte: int) -> int:
    bit = get_seq_bit(ctrl_byte)
    if bit is None:
        raise ValueError(
            f"Cannot make ack for non-data control byte: {to_string(ctrl_byte)}"
        )
    return make_ack(bit)


def is_ack(ctrl_byte: int) -> bool:
    return ctrl_byte & ACK_MASK == ACK_BASE


def is_data(ctrl_byte: int) -> bool:
    return ctrl_byte & DATA_DETECT_MASK == DATA_DETECT_BASE


def is_error(ctrl_byte: int) -> bool:
    return ctrl_byte == ERROR


def is_continuation(ctrl_byte: int) -> bool:
    return bool(ctrl_byte & CONTINUATION_BIT)
