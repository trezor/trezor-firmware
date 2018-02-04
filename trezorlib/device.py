# This file is part of the TREZOR project.
#
# Copyright (C) 2012-2017 Marek Palatinus <slush@satoshilabs.com>
# Copyright (C) 2012-2017 Pavol Rusnak <stick@satoshilabs.com>
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


from .transport_bridge import BridgeTransport
from .transport_hid import HidTransport
from .transport_udp import UdpTransport
from .transport_webusb import WebUsbTransport


class TrezorDevice(object):

    @classmethod
    def enumerate(cls):
        devices = []

        for d in BridgeTransport.enumerate():
            devices.append(d)

        for d in UdpTransport.enumerate():
            devices.append(d)

        for d in HidTransport.enumerate():
            devices.append(d)

        for d in WebUsbTransport.enumerate():
            devices.append(d)

        return devices

    @classmethod
    def find_by_path(cls, path):
        if path is None:
            try:
                return cls.enumerate()[0]
            except IndexError:
                raise Exception("No TREZOR device found")

        prefix = path.split(':')[0]

        if prefix == BridgeTransport.PATH_PREFIX:
            return BridgeTransport.find_by_path(path)

        if prefix == UdpTransport.PATH_PREFIX:
            return UdpTransport.find_by_path(path)

        if prefix == WebUsbTransport.PATH_PREFIX:
            return WebUsbTransport.find_by_path(path)

        if prefix == HidTransport.PATH_PREFIX:
            return HidTransport.find_by_path(path)

        raise Exception("Unknown path prefix '%s'" % prefix)
