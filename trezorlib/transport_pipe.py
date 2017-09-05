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

import os
import time

from .protocol_v1 import ProtocolV1
from .transport import Transport, TransportException


class PipeTransport(Transport):
    '''
    PipeTransport implements fake wire transport over local named pipe.
    Use this transport for talking with trezor-emu.
    '''

    def __init__(self, device=None, is_device=False):
        super(PipeTransport, self).__init__()

        if not device:
            device = '/tmp/pipe.trezor'
        self.device = device
        self.is_device = is_device
        self.filename_read = None
        self.filename_write = None
        self.read_f = None
        self.write_f = None
        self.protocol = ProtocolV1()

    def __str__(self):
        return self.device

    @staticmethod
    def enumerate():
        raise NotImplementedError('This transport cannot enumerate devices')

    @staticmethod
    def find_by_path(path=None):
        return PipeTransport(path)

    def open(self):
        if self.is_device:
            self.filename_read = self.device + '.to'
            self.filename_write = self.device + '.from'
            os.mkfifo(self.filename_read, 0o600)
            os.mkfifo(self.filename_write, 0o600)
        else:
            self.filename_read = self.device + '.from'
            self.filename_write = self.device + '.to'
            if not os.path.exists(self.filename_write):
                raise TransportException('Not connected')

        self.read_f = os.open(self.filename_read, 'rb', 0)
        self.write_f = os.open(self.filename_write, 'w+b', 0)

        self.protocol.session_begin(self)

    def close(self):
        self.protocol.session_end(self)
        if self.read_f:
            self.read_f.close()
            self.read_f = None
        if self.write_f:
            self.write_f.close()
            self.write_f = None
        if self.is_device:
            os.unlink(self.filename_read)
            os.unlink(self.filename_write)
        self.filename_read = None
        self.filename_write = None

    def read(self):
        return self.protocol.read(self)

    def write(self, msg):
        return self.protocol.write(self, msg)

    def write_chunk(self, chunk):
        if len(chunk) != 64:
            raise TransportException('Unexpected chunk size: %d' % len(chunk))
        self.write_f.write(chunk)
        self.write_f.flush()

    def read_chunk(self):
        while True:
            chunk = self.read_f.read(64)
            if chunk:
                break
            else:
                time.sleep(0.001)
        if len(chunk) != 64:
            raise TransportException('Unexpected chunk size: %d' % len(chunk))
        return bytearray(chunk)
