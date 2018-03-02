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
import socket

from .protocol_v1 import ProtocolV1
from .protocol_v2 import ProtocolV2
from .transport import Transport, TransportException


class UdpTransport(Transport):

    DEFAULT_HOST = '127.0.0.1'
    DEFAULT_PORT = 21324
    PATH_PREFIX = 'udp'

    def __init__(self, device=None, protocol=None):
        super(UdpTransport, self).__init__()

        if not device:
            host = UdpTransport.DEFAULT_HOST
            port = UdpTransport.DEFAULT_PORT
        else:
            devparts = device.split(':')
            host = devparts[0]
            port = int(devparts[1]) if len(devparts) > 1 else UdpTransport.DEFAULT_PORT
        if not protocol:
            protocol = ProtocolV1()
        self.device = (host, port)
        self.protocol = protocol
        self.socket = None

    def __str__(self):
        return self.get_path()

    def get_path(self):
        return "%s:%s:%s" % ((self.PATH_PREFIX,) + self.device)

    @staticmethod
    def enumerate():
        devices = []
        d = UdpTransport("%s:%d" % (UdpTransport.DEFAULT_HOST, UdpTransport.DEFAULT_PORT))
        d.open()
        if d._ping():
            devices.append(d)
        d.close()
        return devices

    @classmethod
    def find_by_path(cls, path):
        path = path.replace('%s:' % cls.PATH_PREFIX, '')
        return UdpTransport(path)

    def open(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.connect(self.device)
        self.socket.settimeout(10)
        self.protocol.session_begin(self)

    def close(self):
        if self.socket:
            self.protocol.session_end(self)
            self.socket.close()
            self.socket = None

    def _ping(self):
        '''Test if the device is listening.'''
        resp = None
        try:
            self.socket.sendall(b'PINGPING')
            resp = self.socket.recv(8)
        except:
            pass
        return resp == b'PONGPONG'

    def read(self):
        return self.protocol.read(self)

    def write(self, msg):
        return self.protocol.write(self, msg)

    def write_chunk(self, chunk):
        if len(chunk) != 64:
            raise TransportException('Unexpected data length')
        self.socket.sendall(chunk)

    def read_chunk(self):
        while True:
            try:
                chunk = self.socket.recv(64)
                break
            except socket.timeout:
                continue
        if len(chunk) != 64:
            raise TransportException('Unexpected chunk size: %d' % len(chunk))
        return bytearray(chunk)
