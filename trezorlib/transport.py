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
from . import mapping
import binascii

class NotImplementedException(Exception):
    pass

class ConnectionError(Exception):
    pass

class Transport(object):
    def __init__(self, device, *args, **kwargs):
        self.device = device
        self.session_id = 0
        self.session_depth = 0
        self._open()

    def session_begin(self):
        """
        Apply a lock to the device in order to preform synchronous multistep "conversations" with the device.  For example, before entering the transaction signing workflow, one begins a session.  After the transaction is complete, the session may be ended.
        """
        if self.session_depth == 0:
            self._session_begin()
        self.session_depth += 1

    def session_end(self):
        """
        End a session.  Se session_begin for an in depth description of TREZOR sessions.
        """
        self.session_depth -= 1
        self.session_depth = max(0, self.session_depth)
        if self.session_depth == 0:
            self._session_end()

    def close(self):
        """
        Close the connection to the physical device or file descriptor represented by the Transport.
        """
        self._close()

    def write(self, msg):
        """
        Write mesage to tansport.  msg should be a member of a valid `protobuf class <https://developers.google.com/protocol-buffers/docs/pythontutorial>`_ with a SerializeToString() method.
        """
        raise NotImplementedException("Not implemented")

    def read(self):
        """
        If there is data available to be read from the transport, reads the data and tries to parse it as a protobuf message.  If the parsing succeeds, return a protobuf object.
        Otherwise, returns None.
        """
        if not self._ready_to_read():
            return None

        data = self._read()
        if data is None:
            return None

        return self._parse_message(data)

    def read_blocking(self):
        """
        Same as read, except blocks until data is available to be read.
        """
        while True:
            data = self._read()
            if data != None:
                break

        return self._parse_message(data)

    def _parse_message(self, data):
        (session_id, msg_type, data) = data

        # Raise exception if we get the response with unexpected session ID
        if session_id != self.session_id:
            raise Exception("Session ID mismatch. Have %d, got %d" %
                            (self.session_id, session_id))

        if msg_type == 'protobuf':
            return data
        else:
            inst = mapping.get_class(msg_type)()
            inst.ParseFromString(bytes(data))
            return inst

    # Functions to be implemented in specific transports:
    def _open(self):
        raise NotImplementedException("Not implemented")

    def _close(self):
        raise NotImplementedException("Not implemented")

    def _write_chunk(self, chunk):
        raise NotImplementedException("Not implemented")

    def _read_chunk(self):
        raise NotImplementedException("Not implemented")

    def _ready_to_read(self):
        """
        Returns True if there is data to be read from the transport.  Otherwise, False.
        """
        raise NotImplementedException("Not implemented")

    def _session_begin(self):
        pass

    def _session_end(self):
        pass

class TransportV1(Transport):
    def write(self, msg):
        ser = msg.SerializeToString()
        header = struct.pack(">HL", mapping.get_type(msg), len(ser))
        data = bytearray(b"##" + header + ser)

        while len(data):
            # Report ID, data padded to 63 bytes
            chunk = b'?' + data[:63] + b'\0' * (63 - len(data[:63]))
            self._write_chunk(chunk)
            data = data[63:]

    def _read(self):
        chunk = self._read_chunk()
        (msg_type, datalen, data) = self.parse_first(chunk)

        while len(data) < datalen:
            chunk = self._read_chunk()
            data.extend(self.parse_next(chunk))

        # Strip padding zeros
        data = data[:datalen]
        return (0, msg_type, data)

    def parse_first(self, chunk):
        if chunk[:3] != b"?##":
            raise Exception("Unexpected magic characters")

        try:
            headerlen = struct.calcsize(">HL")
            (msg_type, datalen) = struct.unpack(">HL", bytes(chunk[3:3 + headerlen]))
        except:
            raise Exception("Cannot parse header")

        data = chunk[3 + headerlen:]
        return (msg_type, datalen, data)

    def parse_next(self, chunk):
        if chunk[0:1] != b"?":
            raise Exception("Unexpected magic characters")

        return chunk[1:]

class TransportV2(Transport):
    def write(self, msg):
        if not self.session_id:
            raise Exception('Missing session_id for v2 transport')

        data = bytearray(msg.SerializeToString())

        # Convert to unsigned in python2
        checksum = binascii.crc32(data) & 0xffffffff

        header1 = struct.pack(">L", self.session_id)
        header2 = struct.pack(">LL", mapping.get_type(msg), len(data))
        footer = struct.pack(">L", checksum)

        data = header2 + data + footer

        first = True
        while len(data):
            if first:
                # Magic character, header1, header2, data padded to 64 bytes
                datalen = 63 - len(header1)
                chunk = b'H' + header1 + \
                    data[:datalen] + b'\0' * (datalen - len(data[:datalen]))
            else:
                # Magic character, header1, data padded to 64 bytes
                datalen = 63 - len(header1)
                chunk = b'D' + header1 + \
                    data[:datalen] + b'\0' * (datalen - len(data[:datalen]))

            self._write_chunk(chunk)
            data = data[datalen:]
            first = False

    def _read(self):
        if not self.session_id:
            raise Exception('Missing session_id for v2 transport')

        chunk = self._read_chunk()
        (session_id, msg_type, datalen, data) = self.parse_first(chunk)
        payloadlen = datalen + 4  # For the checksum

        while len(data) < payloadlen:
            chunk = self._read_chunk()
            (next_session_id, next_data) = self.parse_next(chunk)

            if next_session_id != session_id:
                raise Exception("Session id mismatch")

            data.extend(next_data)

        data = data[:payloadlen]  # Strip padding zeros
        footer = data[-4:]
        data = data[:-4]

        csum, = struct.unpack('>L', footer)
        csum_comp = binascii.crc32(data) & 0xffffffff
        if csum != csum_comp:
            raise Exception("Message checksum mismatch. Expected %d, got %d" %
                            (csum_comp, csum))

        return (session_id, msg_type, data)

    def parse_first(self, chunk):
        if chunk[0:1] != b"H":
            raise Exception("Unexpected magic character")

        try:
            headerlen = struct.calcsize(">LLL")
            (session_id, msg_type, datalen) = struct.unpack(">LLL", bytes(chunk[1:1 + headerlen]))
        except:
            raise Exception("Cannot parse header")

        data = chunk[1 + headerlen:]
        return (session_id, msg_type, datalen, data)

    def parse_next(self, chunk):
        if chunk[0:1] != b"D":
            raise Exception("Unexpected magic characters")

        try:
            headerlen = struct.calcsize(">L")
            (session_id,) = struct.unpack(">L", bytes(chunk[1:1 + headerlen]))
        except:
            raise Exception("Cannot parse header")

        data = chunk[1 + headerlen:]
        return (session_id, data)

    def parse_session_open(self, chunk):
        if chunk[0:1] != b"O":
            raise Exception("Unexpected magic character")

        try:
            headerlen = struct.calcsize(">L")
            (session_id,) = struct.unpack(">L", bytes(chunk[1:1 + headerlen]))
        except:
            raise Exception("Cannot parse header")

        return session_id

    def _session_begin(self):
        self._write_chunk(bytearray(b'O' + b'\0' * 63))
        self.session_id = self.parse_session_open(self._read_chunk())

    def _session_end(self):
        header = struct.pack(">L", self.session_id)
        self._write_chunk(bytearray(b'C' + header + b'\0' * (63 - len(header))))
        if self._read_chunk()[0] != ord('C'):
            raise Exception("Expected session close")
        self.session_id = None

    '''
    def read_headers(self, read_f):
        c = read_f.read(2)
        if c != b"?!":
            raise Exception("Unexpected magic characters")

        try:
            headerlen = struct.calcsize(">HL")
            (session_id, msg_type, datalen) = struct.unpack(">LLL", read_f.read(headerlen))
        except:
            raise Exception("Cannot parse header length")

        return (0, msg_type, datalen)
    '''
