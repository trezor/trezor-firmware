# This file is part of the TREZOR project.
#
# Copyright (C) 2012-2016 Marek Palatinus <slush@satoshilabs.com>
# Copyright (C) 2012-2016 Pavol Rusnak <stick@satoshilabs.com>
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import

import struct
from io import BytesIO
from . import messages as proto
from . import mapping
from . import protobuf

REPLEN = 64


class ProtocolV2(object):

    def __init__(self):
        self.session = None

    def session_begin(self, transport):
        chunk = struct.pack('>B', 0x03)
        chunk = chunk.ljust(REPLEN, b'\x00')
        transport.write_chunk(chunk)
        resp = transport.read_chunk()
        self.session = self.parse_session_open(resp)

    def session_end(self, transport):
        if not self.session:
            return
        chunk = struct.pack('>BL', 0x04, self.session)
        chunk = chunk.ljust(REPLEN, b'\x00')
        transport.write_chunk(chunk)
        resp = transport.read_chunk()
        (magic, ) = struct.unpack('>B', resp[:1])
        if magic != 0x04:
            raise RuntimeError('Expected session close')
        self.session = None

    def write(self, transport, msg):
        if not self.session:
            raise RuntimeError('Missing session for v2 protocol')

        # Serialize whole message
        data = BytesIO()
        protobuf.dump_message(data, msg)
        data = data.getvalue()
        dataheader = struct.pack('>LL', mapping.get_type(msg), len(data))
        data = dataheader + data
        seq = -1

        # Write it out
        while data:
            if seq < 0:
                repheader = struct.pack('>BL', 0x01, self.session)
            else:
                repheader = struct.pack('>BLL', 0x02, self.session, seq)
            datalen = REPLEN - len(repheader)
            chunk = repheader + data[:datalen]
            chunk = chunk.ljust(REPLEN, b'\x00')
            transport.write_chunk(chunk)
            data = data[datalen:]
            seq += 1

    def read(self, transport):
        if not self.session:
            raise RuntimeError('Missing session for v2 protocol')

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
        return msg

    def parse_first(self, chunk):
        try:
            headerlen = struct.calcsize('>BLLL')
            (magic, session, msg_type, datalen) = struct.unpack('>BLLL', chunk[:headerlen])
        except:
            raise RuntimeError('Cannot parse header')
        if magic != 0x01:
            raise RuntimeError('Unexpected magic character')
        if session != self.session:
            raise RuntimeError('Session id mismatch')
        return msg_type, datalen, chunk[headerlen:]

    def parse_next(self, chunk):
        try:
            headerlen = struct.calcsize('>BLL')
            (magic, session, sequence) = struct.unpack('>BLL', chunk[:headerlen])
        except:
            raise RuntimeError('Cannot parse header')
        if magic != 0x02:
            raise RuntimeError('Unexpected magic characters')
        if session != self.session:
            raise RuntimeError('Session id mismatch')
        return chunk[headerlen:]

    def parse_session_open(self, chunk):
        try:
            headerlen = struct.calcsize('>BL')
            (magic, session) = struct.unpack('>BL', chunk[:headerlen])
        except:
            raise RuntimeError('Cannot parse header')
        if magic != 0x03:
            raise RuntimeError('Unexpected magic character')
        return session
