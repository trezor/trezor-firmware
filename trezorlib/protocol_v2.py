# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
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

import logging
import struct
from io import BytesIO
from typing import Tuple

from . import mapping, protobuf
from .transport import Transport

REPLEN = 64

LOG = logging.getLogger(__name__)


class ProtocolV2:
    def __init__(self) -> None:
        self.session = None

    def session_begin(self, transport: Transport) -> None:
        chunk = struct.pack(">B", 0x03)
        chunk = chunk.ljust(REPLEN, b"\x00")
        transport.write_chunk(chunk)
        resp = transport.read_chunk()
        self.session = self.parse_session_open(resp)
        LOG.debug("[session {}] session started".format(self.session))

    def session_end(self, transport: Transport) -> None:
        if not self.session:
            return
        chunk = struct.pack(">BL", 0x04, self.session)
        chunk = chunk.ljust(REPLEN, b"\x00")
        transport.write_chunk(chunk)
        resp = transport.read_chunk()
        (magic,) = struct.unpack(">B", resp[:1])
        if magic != 0x04:
            raise RuntimeError("Expected session close")
        LOG.debug("[session {}] session ended".format(self.session))
        self.session = None

    def write(self, transport: Transport, msg: protobuf.MessageType) -> None:
        if not self.session:
            raise RuntimeError("Missing session for v2 protocol")

        LOG.debug(
            "[session {}] sending message: {}".format(
                self.session, msg.__class__.__name__
            ),
            extra={"protobuf": msg},
        )
        # Serialize whole message
        data = BytesIO()
        protobuf.dump_message(data, msg)
        data = data.getvalue()
        dataheader = struct.pack(">LL", mapping.get_type(msg), len(data))
        data = dataheader + data
        seq = -1

        # Write it out
        while data:
            if seq < 0:
                repheader = struct.pack(">BL", 0x01, self.session)
            else:
                repheader = struct.pack(">BLL", 0x02, self.session, seq)
            datalen = REPLEN - len(repheader)
            chunk = repheader + data[:datalen]
            chunk = chunk.ljust(REPLEN, b"\x00")
            transport.write_chunk(chunk)
            data = data[datalen:]
            seq += 1

    def read(self, transport: Transport) -> protobuf.MessageType:
        if not self.session:
            raise RuntimeError("Missing session for v2 protocol")

        # Read header with first part of message data
        chunk = transport.read_chunk()
        msg_type, datalen, data = self.parse_first(chunk)

        # Read the rest of the message
        while len(data) < datalen:
            chunk = transport.read_chunk()
            next_data = self.parse_next(chunk)
            data.extend(next_data)

        # Strip padding
        data = BytesIO(data[:datalen])

        # Parse to protobuf
        msg = protobuf.load_message(data, mapping.get_class(msg_type))
        LOG.debug(
            "[session {}] received message: {}".format(
                self.session, msg.__class__.__name__
            ),
            extra={"protobuf": msg},
        )
        return msg

    def parse_first(self, chunk: bytes) -> Tuple[int, int, bytes]:
        try:
            headerlen = struct.calcsize(">BLLL")
            magic, session, msg_type, datalen = struct.unpack(
                ">BLLL", chunk[:headerlen]
            )
        except Exception:
            raise RuntimeError("Cannot parse header")
        if magic != 0x01:
            raise RuntimeError("Unexpected magic character")
        if session != self.session:
            raise RuntimeError("Session id mismatch")
        return msg_type, datalen, chunk[headerlen:]

    def parse_next(self, chunk: bytes) -> bytes:
        try:
            headerlen = struct.calcsize(">BLL")
            magic, session, sequence = struct.unpack(">BLL", chunk[:headerlen])
        except Exception:
            raise RuntimeError("Cannot parse header")
        if magic != 0x02:
            raise RuntimeError("Unexpected magic characters")
        if session != self.session:
            raise RuntimeError("Session id mismatch")
        return chunk[headerlen:]

    def parse_session_open(self, chunk: bytes) -> int:
        try:
            headerlen = struct.calcsize(">BL")
            magic, session = struct.unpack(">BL", chunk[:headerlen])
        except Exception:
            raise RuntimeError("Cannot parse header")
        if magic != 0x03:
            raise RuntimeError("Unexpected magic character")
        return session
