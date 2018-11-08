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

import sys
import time
from typing import Any, Dict, Iterable

import hid

from . import TransportException
from .protocol import ProtocolBasedTransport, get_protocol

DEV_TREZOR1 = (0x534C, 0x0001)
DEV_TREZOR2 = (0x1209, 0x53C1)
DEV_TREZOR2_BL = (0x1209, 0x53C0)

HidDevice = Dict[str, Any]
HidDeviceHandle = Any


class HidHandle:
    def __init__(self, path: str, probe_hid_version: bool = False) -> None:
        self.path = path
        self.handle = None  # type: HidDeviceHandle
        self.hid_version = None if probe_hid_version else 2

    def open(self) -> None:
        self.handle = hid.device()
        try:
            self.handle.open_path(self.path)
        except (IOError, OSError) as e:
            if sys.platform.startswith("linux"):
                e.args = e.args + (
                    "Do you have udev rules installed? https://github.com/trezor/trezor-common/blob/master/udev/51-trezor.rules",
                )
            raise e
        self.handle.set_nonblocking(True)

        if self.hid_version is None:
            self.hid_version = self.probe_hid_version()

    def close(self) -> None:
        if self.handle is not None:
            self.handle.close()
        self.handle = None

    def write_chunk(self, chunk: bytes) -> None:
        if len(chunk) != 64:
            raise TransportException("Unexpected chunk size: %d" % len(chunk))

        if self.hid_version == 2:
            self.handle.write(b"\0" + bytearray(chunk))
        else:
            self.handle.write(chunk)

    def read_chunk(self) -> bytes:
        while True:
            chunk = self.handle.read(64)
            if chunk:
                break
            else:
                time.sleep(0.001)
        if len(chunk) != 64:
            raise TransportException("Unexpected chunk size: %d" % len(chunk))
        return chunk

    def probe_hid_version(self) -> int:
        n = self.handle.write([0, 63] + [0xFF] * 63)
        if n == 65:
            return 2
        n = self.handle.write([63] + [0xFF] * 63)
        if n == 64:
            return 1
        raise TransportException("Unknown HID version")


class HidTransport(ProtocolBasedTransport):
    """
    HidTransport implements transport over USB HID interface.
    """

    PATH_PREFIX = "hid"

    def __init__(self, device: HidDevice, hid_handle: HidHandle = None) -> None:
        if hid_handle is None:
            hid_handle = HidHandle(device["path"])

        self.device = device
        self.hid = hid_handle

        protocol = get_protocol(hid_handle, is_trezor2(device))
        super().__init__(protocol=protocol)

    def get_path(self) -> str:
        return "%s:%s" % (self.PATH_PREFIX, self.device["path"].decode())

    @classmethod
    def enumerate(cls, debug: bool = False) -> Iterable["HidTransport"]:
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

    def find_debug(self) -> "HidTransport":
        if self.protocol.VERSION >= 2:
            # use the same device
            return self
        else:
            # For v1 protocol, find debug USB interface for the same serial number
            for debug in HidTransport.enumerate(debug=True):
                if debug.device["serial_number"] == self.device["serial_number"]:
                    return debug
            raise TransportException("Debug HID device not found")


def is_trezor1(dev: HidDevice) -> bool:
    return (dev["vendor_id"], dev["product_id"]) == DEV_TREZOR1


def is_trezor2(dev: HidDevice) -> bool:
    return (dev["vendor_id"], dev["product_id"]) == DEV_TREZOR2


def is_trezor2_bl(dev: HidDevice) -> bool:
    return (dev["vendor_id"], dev["product_id"]) == DEV_TREZOR2_BL


def is_wirelink(dev: HidDevice) -> bool:
    return dev["usage_page"] == 0xFF00 or dev["interface_number"] == 0


def is_debuglink(dev: HidDevice) -> bool:
    return dev["usage_page"] == 0xFF01 or dev["interface_number"] == 1


TRANSPORT = HidTransport
