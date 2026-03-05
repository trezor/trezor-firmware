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
MESSAGE_TYPE_LENGTH = 2

CONTINUATION_PACKET = 0x80

DEFAULT_MAX_RETRIES = 10

LOG = logging.getLogger(__name__)


class ReceivedMessage(t.NamedTuple):
    ctrl_byte: int
    cid: int
    data_length: int
    data: bytearray


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
    while True:
        # Process header with first part of message data
        chunk = transport.read_chunk(timeout=timeout)
        while True:
            try:
                ctrl_byte, cid, data_length = struct.unpack(
                    FORMAT_STR_INIT, chunk[:INIT_HEADER_LENGTH]
                )
            except struct.error:
                raise exceptions.ProtocolError("Invalid message header")

            if ctrl_byte == CONTINUATION_PACKET:
                LOG.warning("Skipping unexpected continuation packet")
                break

            received = ReceivedMessage(
                ctrl_byte, cid, data_length, bytearray(chunk[INIT_HEADER_LENGTH:])
            )

            # Process the rest of the message
            while True:
                if len(received.data) >= received.data_length:
                    # Enough data has been received
                    return Message.parse(
                        received.ctrl_byte,
                        received.cid,
                        bytes(received.data[: received.data_length]),
                    )

                chunk = transport.read_chunk(timeout=timeout)
                try:
                    ctrl_byte, cid = struct.unpack(
                        FORMAT_STR_CONT, chunk[:CONT_HEADER_LENGTH]
                    )
                except struct.error:
                    raise exceptions.ProtocolError("Invalid continuation header")
                if ctrl_byte != CONTINUATION_PACKET:
                    LOG.warning(
                        "Expected continuation, got: %s",
                        control_byte.to_string(ctrl_byte),
                    )
                    # Keep the unexpected chunk for to be re-processed by the outer loop
                    break

                if received.cid != cid:
                    LOG.warning(
                        "Ignoring packet for channel %s (wanted %s)", cid, received.cid
                    )
                    continue

                received.data.extend(chunk[CONT_HEADER_LENGTH:])
