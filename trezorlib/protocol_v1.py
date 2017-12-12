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

from io import BytesIO
import struct
from . import mapping
from . import protobuf

REPLEN = 64


class ProtocolV1(object):

    def session_begin(self, transport):
        pass

    def session_end(self, transport):
        pass

    def write(self, transport, msg):
        data = BytesIO()
        protobuf.dump_message(data, msg)
        ser = data.getvalue()
        header = struct.pack(">HL", mapping.get_type(msg), len(ser))
        data = bytearray(b"##" + header + ser)

        while data:
            # Report ID, data padded to 63 bytes
            chunk = b'?' + data[:REPLEN - 1]
            chunk = chunk.ljust(REPLEN, b'\x00')
            transport.write_chunk(chunk)
            data = data[63:]

    def read(self, transport):
        # Read header with first part of message data
        chunk = transport.read_chunk()
        (msg_type, datalen, data) = self.parse_first(chunk)

        # Read the rest of the message
        while len(data) < datalen:
            chunk = transport.read_chunk()
            data.extend(self.parse_next(chunk))

        # Strip padding
        data = BytesIO(data[:datalen])

        # Parse to protobuf
        msg = protobuf.load_message(data, mapping.get_class(msg_type))
        return msg

    def parse_first(self, chunk):
        if chunk[:3] != b'?##':
            raise RuntimeError('Unexpected magic characters')
        try:
            headerlen = struct.calcsize('>HL')
            (msg_type, datalen) = struct.unpack('>HL', chunk[3:3 + headerlen])
        except:
            raise RuntimeError('Cannot parse header')

        data = chunk[3 + headerlen:]
        return (msg_type, datalen, data)

    def parse_next(self, chunk):
        if chunk[:1] != b'?':
            raise RuntimeError('Unexpected magic characters')
        return chunk[1:]
