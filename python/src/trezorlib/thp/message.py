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

import io
import struct
import typing as t
import zlib
from dataclasses import dataclass
from functools import cached_property

from typing_extensions import Self

from .. import exceptions
from . import control_byte

TREZOR_STATE_UNPAIRED = b"\x00"
TREZOR_STATE_PAIRED = b"\x01"

BROADCAST_CHANNEL_ID = 0xFFFF

FORMAT_STR_INIT = ">BHH"
FORMAT_STR_CONT = ">BH"

CHECKSUM_LENGTH = 4


def packet_header(ctrl_byte: int, cid: int) -> bytes:
    return struct.pack(">BH", ctrl_byte, cid)


def packet_length(data: bytes) -> bytes:
    return struct.pack(">H", len(data) + CHECKSUM_LENGTH)


def _crc32(data: bytes) -> bytes:
    return zlib.crc32(data).to_bytes(CHECKSUM_LENGTH, "big")


class ChecksumError(exceptions.ProtocolError):
    """Invalid checksum in message."""

    def __init__(self, message: Message, received_checksum: bytes) -> None:
        self.message = message
        self.received_checksum = received_checksum
        super().__init__(message, received_checksum)


@dataclass(frozen=True)
class Message:
    ctrl_byte: int
    cid: int
    data: bytes

    @staticmethod
    def checked_bytes(ctrl_byte: int, cid: int, data: bytes) -> bytes:
        return packet_header(ctrl_byte, cid) + packet_length(data) + data

    def checksum(self) -> bytes:
        return _crc32(self.checked_bytes(self.ctrl_byte, self.cid, self.data))

    def __str__(self) -> str:
        props = {
            "ctrl": control_byte.to_string(self.ctrl_byte),
            "cid": f"0x{self.cid:04x}",
            "data": self.data.hex(),
        }
        props_str = ", ".join(f"{k}={v}" for k, v in props.items())
        return f"Message({props_str})"

    def to_bytes(self) -> bytes:
        """Return the message as a single byte string with the appropriate header."""
        return self.checked_bytes(self.ctrl_byte, self.cid, self.data) + self.checksum()

    def chunks(self, chunk_size: int) -> t.Iterator[bytes]:
        """Yield chunks of the message, properly delineated by the right
        control bytes and padded to the chunk size.
        """
        payload_reader = io.BytesIO(self.to_bytes())
        first_chunk = payload_reader.read(chunk_size)
        yield first_chunk.ljust(chunk_size, b"\x00")

        cont_header = packet_header(control_byte.CONTINUATION_BIT, self.cid)
        cont_chunk_size = chunk_size - len(cont_header)
        while buffer := payload_reader.read(cont_chunk_size):
            chunk = cont_header + buffer
            yield chunk.ljust(chunk_size, b"\x00")

    @classmethod
    def parse(cls, ctrl_byte: int, cid: int, payload: bytes) -> Self:
        if len(payload) < CHECKSUM_LENGTH:
            raise exceptions.ProtocolError("Payload too short")
        data, checksum = payload[:-CHECKSUM_LENGTH], payload[-CHECKSUM_LENGTH:]
        new = cls(ctrl_byte, cid, data)
        if new.checksum() != checksum:
            raise ChecksumError(new, checksum)
        return new

    @classmethod
    def ack(cls, cid: int, ack_bit: bool) -> Self:
        return cls(control_byte.make_ack(ack_bit), cid, b"")

    @classmethod
    def broadcast(cls, ctrl_byte: int, data: bytes) -> Self:
        return cls(ctrl_byte, BROADCAST_CHANNEL_ID, data)

    def with_seq_bit(self, seq_bit: bool) -> Self:
        return self.__class__(
            control_byte.set_seq_bit(self.ctrl_byte, seq_bit),
            self.cid,
            self.data,
        )

    @cached_property
    def seq_bit(self) -> bool | None:
        return control_byte.get_seq_bit(self.ctrl_byte)

    @cached_property
    def ack_bit(self) -> bool | None:
        return control_byte.get_ack_bit(self.ctrl_byte)

    def is_ack(self) -> bool:
        return control_byte.is_ack(self.ctrl_byte)

    def is_channel_allocation_response(self) -> bool:
        return (
            self.cid == BROADCAST_CHANNEL_ID
            and self.ctrl_byte == control_byte.CHANNEL_ALLOCATION_RES
        )

    def is_pong(self) -> bool:
        return self.cid == BROADCAST_CHANNEL_ID and self.ctrl_byte == control_byte.PONG

    def is_handshake_init_response(self) -> bool:
        return (
            self.ctrl_byte & control_byte.DATA_MASK == control_byte.HANDSHAKE_INIT_RES
        )

    def is_handshake_comp_response(self) -> bool:
        return (
            self.ctrl_byte & control_byte.DATA_MASK == control_byte.HANDSHAKE_COMP_RES
        )

    def is_encrypted_transport(self) -> bool:
        return (
            self.ctrl_byte & control_byte.DATA_MASK == control_byte.ENCRYPTED_TRANSPORT
        )
