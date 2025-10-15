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

import logging
import struct
import time
import typing as t

from .. import client, exceptions
from ..transport import Timeout, Transport
from . import control_byte
from .message import FORMAT_STR_CONT, FORMAT_STR_INIT, ChecksumError, Message

INIT_HEADER_LENGTH = 5
CONT_HEADER_LENGTH = 3
MAX_PAYLOAD_LEN = 60000
MESSAGE_TYPE_LENGTH = 2

CONTINUATION_PACKET = 0x80

DEFAULT_MAX_RETRIES = 10

LOG = logging.getLogger(__name__)


class FirstPacket(t.NamedTuple):
    ctrl_byte: int
    cid: int
    data_length: int
    data: bytes


def write_payload_to_wire(transport: Transport, message: Message) -> None:
    if transport.CHUNK_SIZE is None:
        transport.write_chunk(message.to_bytes())
        return

    for chunk in message.chunks(transport.CHUNK_SIZE):
        transport.write_chunk(chunk)


def read(
    transport: Transport,
    timeout: float | None = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> Message:
    if timeout is None:
        timeout = client._DEFAULT_READ_TIMEOUT
    start = time.monotonic()
    for _ in range(1 + max_retries):
        try:
            return read_and_assemble(transport, timeout)
        except ChecksumError as e:
            LOG.warning(
                "Received message with invalid checksum: %s (expected %s, actual %s)",
                e.message,
                e.message.checksum().hex(),
                e.received_checksum.hex(),
            )
        if timeout is not None and time.monotonic() - start > timeout:
            raise Timeout("Timeout while reading message")
    raise Timeout("Max retries exceeded waiting for a message with a valid checksum")


def read_and_assemble(transport: Transport, timeout: float | None = None) -> Message:
    """
    Reads from the given wire transport.

    Returns `Tuple[MessageHeader, bytes, bytes]`:
        1. `header` (`MessageHeader`): Header of the message.
        2. `data` (`bytes`): Contents of the message (if any).
        3. `checksum` (`bytes`): crc32 checksum of the header + data.

    """
    buffer = bytearray()

    # Read header with first part of message data
    head = read_first(transport, timeout)
    buffer.extend(head.data)

    # Read the rest of the message
    while len(buffer) < head.data_length:
        buffer.extend(read_next(transport, head.cid, timeout))

    msg = Message.parse(head.ctrl_byte, head.cid, bytes(buffer[: head.data_length]))
    return msg


def read_first(transport: Transport, timeout: float | None = None) -> FirstPacket:
    chunk = transport.read_chunk(timeout=timeout)
    try:
        ctrl_byte, cid, data_length = struct.unpack(
            FORMAT_STR_INIT, chunk[:INIT_HEADER_LENGTH]
        )
    except struct.error:
        raise exceptions.ProtocolError("Invalid header")

    data = chunk[INIT_HEADER_LENGTH:]
    return FirstPacket(ctrl_byte, cid, data_length, data)


def read_next(transport: Transport, cid: int, timeout: float | None = None) -> bytes:
    chunk = transport.read_chunk(timeout=timeout)
    ctrl_byte, read_cid = struct.unpack(FORMAT_STR_CONT, chunk[:CONT_HEADER_LENGTH])
    if read_cid != cid:
        LOG.warning("Ignoring packet for channel %s (wanted %s)", read_cid, cid)
        return b""
    if ctrl_byte != CONTINUATION_PACKET:
        raise exceptions.ProtocolError(
            f"Expected continuation, got: {control_byte.to_string(ctrl_byte)}"
        )
    return chunk[CONT_HEADER_LENGTH:]
