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

import os
import socket

from ..protocol_v1 import ProtocolV1
from ..protocol_v2 import ProtocolV2
from . import Transport, TransportException


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

    def get_path(self):
        return "%s:%s:%s" % ((self.PATH_PREFIX,) + self.device)

    def find_debug(self):
        host, port = self.device
        return UdpTransport('{}:{}'.format(host, port + 1), self.protocol)

    @classmethod
    def _try_path(cls, path):
        d = cls(path)
        try:
            d.open()
            if d._ping():
                return d
            else:
                raise TransportException('No TREZOR device found at address {}'.format(path))
        finally:
            d.close()

    @classmethod
    def enumerate(cls):
        default_path = '{}:{}'.format(cls.DEFAULT_HOST, cls.DEFAULT_PORT)
        try:
            return [cls._try_path(default_path)]
        except TransportException:
            return []

    @classmethod
    def find_by_path(cls, path, prefix_search=False):
        if prefix_search:
            return super().find_by_path(path, prefix_search)
        else:
            path = path.replace('{}:'.format(cls.PATH_PREFIX), '')
            return cls._try_path(path)

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


TRANSPORT = UdpTransport
