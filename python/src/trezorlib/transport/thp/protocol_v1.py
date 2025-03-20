# This file is part of the Trezor project.
#
# Copyright (C) 2012-2025 SatoshiLabs and contributors
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
import typing as t

from ... import exceptions, messages
from ...log import DUMP_BYTES
from .protocol_and_channel import Channel

LOG = logging.getLogger(__name__)


class UnexpectedMagicError(RuntimeError):
    pass


class ProtocolV1Channel(Channel):
    _DEFAULT_READ_TIMEOUT: t.ClassVar[float | None] = None
    HEADER_LEN: t.ClassVar[int] = struct.calcsize(">HL")
    _features: messages.Features | None = None

    def get_features(self) -> messages.Features:
        if self._features is None:
            self.update_features()
        assert self._features is not None
        return self._features

    def update_features(self) -> None:
        self.write(messages.GetFeatures())
        resp = self.read()
        if not isinstance(resp, messages.Features):
            raise exceptions.TrezorException("Unexpected response to GetFeatures")
        self._features = resp

    def read(self, timeout: float | None = None) -> t.Any:
        msg_type, msg_bytes = self._read(timeout=timeout)
        LOG.log(
            DUMP_BYTES,
            f"received type {msg_type} ({len(msg_bytes)} bytes): {msg_bytes.hex()}",
        )
        msg = self.mapping.decode(msg_type, msg_bytes)
        LOG.debug(
            f"received message: {msg.__class__.__name__}",
            extra={"protobuf": msg},
        )
        return msg

    def write(self, msg: t.Any) -> None:
        LOG.debug(
            f"sending message: {msg.__class__.__name__}",
            extra={"protobuf": msg},
        )
        msg_type, msg_bytes = self.mapping.encode(msg)
        LOG.log(
            DUMP_BYTES,
            f"encoded as type {msg_type} ({len(msg_bytes)} bytes): {msg_bytes.hex()}",
        )
        self._write(msg_type, msg_bytes)

    def _write(self, message_type: int, message_data: bytes) -> None:
        chunk_size = self.transport.CHUNK_SIZE
        header = struct.pack(">HL", message_type, len(message_data))

        if chunk_size is None:
            self.transport.write_chunk(header + message_data)
            return

        buffer = bytearray(b"##" + header + message_data)
        while buffer:
            # Report ID, data padded to (chunk_size - 1) bytes
            chunk = b"?" + buffer[: chunk_size - 1]
            chunk = chunk.ljust(chunk_size, b"\x00")
            self.transport.write_chunk(chunk)
            buffer = buffer[chunk_size - 1 :]

    def _read(self, timeout: float | None = None) -> t.Tuple[int, bytes]:
        if timeout is None:
            timeout = self._DEFAULT_READ_TIMEOUT

        if self.transport.CHUNK_SIZE is None:
            return self.read_chunkless(timeout=timeout)

        buffer = bytearray()
        # Read header with first part of message data
        msg_type, datalen, first_chunk = self.read_first(timeout=timeout)
        buffer.extend(first_chunk)

        # Read the rest of the message
        while len(buffer) < datalen:
            buffer.extend(self.read_next(timeout=timeout))

        return msg_type, buffer[:datalen]

    def read_chunkless(self, timeout: float | None = None) -> t.Tuple[int, bytes]:
        data = self.transport.read_chunk(timeout=timeout)
        msg_type, datalen = struct.unpack(">HL", data[: self.HEADER_LEN])
        return msg_type, data[self.HEADER_LEN : self.HEADER_LEN + datalen]

    def read_first(self, timeout: float | None = None) -> t.Tuple[int, int, bytes]:
        chunk = self.transport.read_chunk(timeout=timeout)
        if chunk[:3] != b"?##":
            raise UnexpectedMagicError(chunk.hex())
        try:
            msg_type, datalen = struct.unpack(">HL", chunk[3 : 3 + self.HEADER_LEN])
        except Exception:
            raise RuntimeError(f"Cannot parse header: {chunk.hex()}")

        data = chunk[3 + self.HEADER_LEN :]
        return msg_type, datalen, data

    def read_next(self, timeout: float | None = None) -> bytes:
        chunk = self.transport.read_chunk(timeout=timeout)
        if chunk[:1] != b"?":
            raise UnexpectedMagicError(chunk.hex())
        return chunk[1:]
