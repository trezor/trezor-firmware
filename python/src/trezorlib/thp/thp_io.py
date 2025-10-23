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

import struct

from ...exceptions import ThpError
from .. import Transport
from ..thp import checksum
from .message_header import MessageHeader

INIT_HEADER_LENGTH = 5
CONT_HEADER_LENGTH = 3
MAX_PAYLOAD_LEN = 60000
MESSAGE_TYPE_LENGTH = 2

CONTINUATION_PACKET = 0x80


def write_payload_to_wire_and_add_checksum(
    transport: Transport, header: MessageHeader, payload: bytes
) -> None:
    chksum = checksum.compute(header.to_bytes_init() + payload)
    data = payload + chksum
    if len(data) > MAX_PAYLOAD_LEN:
        raise RuntimeError("Message too large")
    write_payload_to_wire(transport, header, data)


def write_payload_to_wire(
    transport: Transport, header: MessageHeader, payload: bytes
) -> None:
    if transport.CHUNK_SIZE is None:
        transport.write_chunk(payload)
        return

    chunk = (
        header.to_bytes_init() + payload[: transport.CHUNK_SIZE - INIT_HEADER_LENGTH]
    )
    chunk = chunk.ljust(transport.CHUNK_SIZE, b"\x00")
    transport.write_chunk(chunk)

    buffer = payload[transport.CHUNK_SIZE - INIT_HEADER_LENGTH :]
    while buffer:
        chunk = (
            header.to_bytes_cont() + buffer[: transport.CHUNK_SIZE - CONT_HEADER_LENGTH]
        )
        chunk = chunk.ljust(transport.CHUNK_SIZE, b"\x00")
        transport.write_chunk(chunk)
        buffer = buffer[transport.CHUNK_SIZE - CONT_HEADER_LENGTH :]


def read(
    transport: Transport, timeout: float | None = None
) -> tuple[MessageHeader, bytes, bytes]:
    """
    Reads from the given wire transport.

    Returns `Tuple[MessageHeader, bytes, bytes]`:
        1. `header` (`MessageHeader`): Header of the message.
        2. `data` (`bytes`): Contents of the message (if any).
        3. `checksum` (`bytes`): crc32 checksum of the header + data.

    """
    buffer = bytearray()

    # Read header with first part of message data
    header, first_chunk = read_first(transport, timeout)
    buffer.extend(first_chunk)

    # Read the rest of the message
    while len(buffer) < header.data_length:
        buffer.extend(read_next(transport, header.cid, timeout))

    data_len = header.data_length - checksum.CHECKSUM_LENGTH
    msg_data = buffer[:data_len]
    chksum = buffer[data_len : data_len + checksum.CHECKSUM_LENGTH]

    return (header, bytes(msg_data), bytes(chksum))


def read_first(
    transport: Transport, timeout: float | None = None
) -> tuple[MessageHeader, bytes]:
    chunk = transport.read_chunk(timeout)
    try:
        ctrl_byte, cid, data_length = struct.unpack(
            MessageHeader.format_str_init, chunk[:INIT_HEADER_LENGTH]
        )
    except Exception:
        raise RuntimeError("Cannot parse header")

    data = chunk[INIT_HEADER_LENGTH:]
    return MessageHeader(ctrl_byte, cid, data_length), data


def read_next(transport: Transport, cid: int, timeout: float | None = None) -> bytes:
    chunk = transport.read_chunk(timeout)
    ctrl_byte, read_cid = struct.unpack(
        MessageHeader.format_str_cont, chunk[:CONT_HEADER_LENGTH]
    )
    if ctrl_byte != CONTINUATION_PACKET:
        raise ThpError("Continuation packet with incorrect control byte")
    if read_cid != cid:
        raise ThpError("Continuation packet for different channel")

    return chunk[CONT_HEADER_LENGTH:]
