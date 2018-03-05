# This file is part of the TREZOR project.
#
# Copyright (C) 2012-2016 Marek Palatinus <slush@satoshilabs.com>
# Copyright (C) 2012-2016 Pavol Rusnak <stick@satoshilabs.com>
# Copyright (C) 2016      Jochen Hoenicke <hoenicke@gmail.com>
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


class TransportException(Exception):
    pass


class Transport(object):

    def __init__(self):
        self.session_counter = 0

    def __str__(self):
        return self.get_path()

    def get_path(self):
        return '{}:{}'.format(self.PATH_PREFIX, self.device)

    def session_begin(self):
        if self.session_counter == 0:
            self.open()
        self.session_counter += 1

    def session_end(self):
        self.session_counter = max(self.session_counter - 1, 0)
        if self.session_counter == 0:
            self.close()

    def open(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

    @classmethod
    def enumerate(cls):
        raise NotImplementedError

    @classmethod
    def find_by_path(cls, path, prefix_search=False):
        for device in cls.enumerate():
            if path is None or device.get_path() == path \
                    or (prefix_search and device.get_path().startswith(path)):
                return device

        raise TransportException('{} device not found: {}'.format(cls.PATH_PREFIX, path))


def all_transports():
    from .bridge import BridgeTransport
    from .hid import HidTransport
    from .udp import UdpTransport
    from .webusb import WebUsbTransport
    return (BridgeTransport, HidTransport, UdpTransport, WebUsbTransport)


def enumerate_devices():
    return [device
            for transport in all_transports()
            for device in transport.enumerate()]


def get_transport(path=None, prefix_search=False):
    if path is None:
        try:
            return enumerate_devices()[0]
        except IndexError:
            raise Exception("No TREZOR device found") from None

    # Find whether B is prefix of A (transport name is part of the path)
    # or A is prefix of B (path is a prefix, or a name, of transport).
    # This naively expects that no two transports have a common prefix.
    def match_prefix(a, b):
        return a.startswith(b) or b.startswith(a)

    transports = [t for t in all_transports() if match_prefix(path, t.PATH_PREFIX)]
    if transports:
        return transports[0].find_by_path(path, prefix_search=prefix_search)

    raise Exception("Unknown path prefix '%s'" % prefix)
