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

from .protocol_v1 import ProtocolV1
from .protocol_v2 import ProtocolV2
from .transport import Transport

DEV_TREZOR1 = (0x534c, 0x0001)
DEV_TREZOR2 = (0x1209, 0x53c0)
DEV_TREZOR2_BL = (0x1209, 0x1201)


class HidTransport(Transport):
    '''
    HidTransport implements transport over USB HID interface.
    '''

    def __init__(self, device, protocol=None):
        super(HidTransport, self).__init__()

        if protocol is None:
            if is_trezor2(device):
                protocol = ProtocolV2()
            else:
                protocol = ProtocolV1()
        self.device = device
        self.protocol = protocol
        self.hid = None
        self.hid_version = None

    def __str__(self):
        return self.device['path']

    @staticmethod
    def enumerate(debug=False):
        return [
            HidTransport(dev) for dev in hid.enumerate(0, 0)
            if ((is_trezor1(dev) or is_trezor2(dev) or is_trezor2_bl(dev)) and
                (is_debug(dev) == debug))
        ]

    @staticmethod
    def find_by_path(path=None):
        for transport in HidTransport.enumerate():
            if path is None or transport.device['path'] == path:
                return transport
        raise Exception('HID device not found')

    def find_debug(self):
        if isinstance(self.protocol, ProtocolV2):
            # For v2 protocol, lets use the same HID interface, but with a different session
            debug = HidTransport(self.device, ProtocolV2())
            debug.hid = self.hid
            debug.hid_version = self.hid_version
            return debug
        if isinstance(self.protocol, ProtocolV1):
            # For v1 protocol, find debug USB interface for the same serial number
            for debug in HidTransport.enumerate(debug=True):
                if debug.device['serial_number'] == self.device['serial_number']:
                    return debug

    def open(self):
        if self.hid:
            return
        self.hid = hid.device()
        self.hid.open_path(self.device['path'])
        self.hid.set_nonblocking(True)
        if is_trezor1(self.device):
            self.hid_version = self.probe_hid_version()
        else:
            self.hid_version = 2
        self.protocol.session_begin(self)

    def close(self):
        self.protocol.session_end(self)
        try:
            self.hid.close()
        except OSError:
            pass  # Failing to close the handle is not a problem
        self.hid = None
        self.hid_version = None

    def read(self):
        return self.protocol.read(self)

    def write(self, msg):
        return self.protocol.write(self, msg)

    def write_chunk(self, chunk):
        if len(chunk) != 64:
            raise Exception('Unexpected chunk size: %d' % len(chunk))
        if self.hid_version == 2:
            self.hid.write(b'\0' + chunk)
        else:
            self.hid.write(chunk)

    def read_chunk(self):
        while True:
            chunk = self.hid.read(64)
            if chunk:
                break
            else:
                time.sleep(0.001)
        if len(chunk) != 64:
            raise Exception('Unexpected chunk size: %d' % len(chunk))
        return bytearray(chunk)

    def probe_hid_version(self):
        n = self.hid.write([0, 63] + [0xFF] * 63)
        if n == 65:
            return 2
        n = self.hid.write([63] + [0xFF] * 63)
        if n == 64:
            return 1
        raise Exception('Unknown HID version')


def is_trezor1(dev):
    return (dev['vendor_id'], dev['product_id']) == DEV_TREZOR1


def is_trezor2(dev):
    return (dev['vendor_id'], dev['product_id']) == DEV_TREZOR2


def is_trezor2_bl(dev):
    return (dev['vendor_id'], dev['product_id']) == DEV_TREZOR2_BL


def is_debug(dev):
    return (dev['usage_page'] == 0xFF01 or dev['interface_number'] == 1)
