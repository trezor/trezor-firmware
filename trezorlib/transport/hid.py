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

import time
import hid
import os

from .protocol_v1 import ProtocolV1
from .protocol_v2 import ProtocolV2
from .transport import Transport, TransportException

DEV_TREZOR1 = (0x534c, 0x0001)
DEV_TREZOR2 = (0x1209, 0x53c1)
DEV_TREZOR2_BL = (0x1209, 0x53c0)


class HidHandle(object):

    def __init__(self, path):
        self.path = path
        self.count = 0
        self.handle = None

    def open(self):
        if self.count == 0:
            self.handle = hid.device()
            self.handle.open_path(self.path)
            self.handle.set_nonblocking(True)
        self.count += 1

    def close(self):
        if self.count == 1:
            self.handle.close()
        if self.count > 0:
            self.count -= 1


class HidTransport(Transport):
    '''
    HidTransport implements transport over USB HID interface.
    '''

    PATH_PREFIX = 'hid'

    def __init__(self, device, protocol=None, hid_handle=None):
        super(HidTransport, self).__init__()

        if hid_handle is None:
            hid_handle = HidHandle(device['path'])

        if protocol is None:
            # force_v1 = os.environ.get('TREZOR_TRANSPORT_V1', '0')
            force_v1 = True

            if is_trezor2(device) and not int(force_v1):
                protocol = ProtocolV2()
            else:
                protocol = ProtocolV1()

        self.device = device
        self.protocol = protocol
        self.hid = hid_handle
        self.hid_version = None

    def __str__(self):
        return self.get_path()

    def get_path(self):
        return "%s:%s" % (self.PATH_PREFIX, self.device['path'].decode())

    @staticmethod
    def enumerate(debug=False):
        devices = []
        for dev in hid.enumerate(0, 0):
            if not (is_trezor1(dev) or is_trezor2(dev) or is_trezor2_bl(dev)):
                continue
            if debug:
                if not is_debuglink(dev):
                    continue
            else:
                if not is_wirelink(dev):
                    continue
            devices.append(HidTransport(dev))
        return devices

    @classmethod
    def find_by_path(cls, path):
        if isinstance(path, str):
            path = path.encode()
        path = path.replace(b'%s:' % cls.PATH_PREFIX.encode(), b'')

        for transport in HidTransport.enumerate():
            if path is None or transport.device['path'] == path:
                return transport
        raise TransportException('HID device not found')

    def find_debug(self):
        if isinstance(self.protocol, ProtocolV2):
            # For v2 protocol, lets use the same HID interface, but with a different session
            protocol = ProtocolV2()
            debug = HidTransport(self.device, protocol, self.hid)
            return debug
        if isinstance(self.protocol, ProtocolV1):
            # For v1 protocol, find debug USB interface for the same serial number
            for debug in HidTransport.enumerate(debug=True):
                if debug.device['serial_number'] == self.device['serial_number']:
                    return debug
        raise TransportException('Debug HID device not found')

    def open(self):
        self.hid.open()
        if is_trezor1(self.device):
            self.hid_version = self.probe_hid_version()
        else:
            self.hid_version = 2
        self.protocol.session_begin(self)

    def close(self):
        self.protocol.session_end(self)
        self.hid.close()
        self.hid_version = None

    def read(self):
        return self.protocol.read(self)

    def write(self, msg):
        return self.protocol.write(self, msg)

    def write_chunk(self, chunk):
        if len(chunk) != 64:
            raise TransportException('Unexpected chunk size: %d' % len(chunk))
        if self.hid_version == 2:
            self.hid.handle.write(b'\0' + bytearray(chunk))
        else:
            self.hid.handle.write(chunk)

    def read_chunk(self):
        while True:
            chunk = self.hid.handle.read(64)
            if chunk:
                break
            else:
                time.sleep(0.001)
        if len(chunk) != 64:
            raise TransportException('Unexpected chunk size: %d' % len(chunk))
        return bytearray(chunk)

    def probe_hid_version(self):
        n = self.hid.handle.write([0, 63] + [0xFF] * 63)
        if n == 65:
            return 2
        n = self.hid.handle.write([63] + [0xFF] * 63)
        if n == 64:
            return 1
        raise TransportException('Unknown HID version')


def is_trezor1(dev):
    return (dev['vendor_id'], dev['product_id']) == DEV_TREZOR1


def is_trezor2(dev):
    return (dev['vendor_id'], dev['product_id']) == DEV_TREZOR2


def is_trezor2_bl(dev):
    return (dev['vendor_id'], dev['product_id']) == DEV_TREZOR2_BL


def is_wirelink(dev):
    return (dev['usage_page'] == 0xFF00 or dev['interface_number'] == 0)


def is_debuglink(dev):
    return (dev['usage_page'] == 0xFF01 or dev['interface_number'] == 1)
