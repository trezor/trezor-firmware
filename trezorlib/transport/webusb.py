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

import atexit
import logging
import sys
import time
from typing import Iterable, Optional

from . import TREZORS, UDEV_RULES_STR, TransportException
from .protocol import ProtocolBasedTransport, ProtocolV1

LOG = logging.getLogger(__name__)

try:
    import usb1
except Exception as e:
    LOG.warning("WebUSB transport is disabled: {}".format(e))
    usb1 = None

if False:
    # mark Optional as used, otherwise it only exists in comments
    Optional

INTERFACE = 0
ENDPOINT = 1
DEBUG_INTERFACE = 1
DEBUG_ENDPOINT = 2


class WebUsbHandle:
    def __init__(self, device: "usb1.USBDevice", debug: bool = False) -> None:
        self.device = device
        self.interface = DEBUG_INTERFACE if debug else INTERFACE
        self.endpoint = DEBUG_ENDPOINT if debug else ENDPOINT
        self.count = 0
        self.handle = None  # type: Optional[usb1.USBDeviceHandle]

    def open(self) -> None:
        self.handle = self.device.open()
        if self.handle is None:
            if sys.platform.startswith("linux"):
                args = (UDEV_RULES_STR,)
            else:
                args = ()
            raise IOError("Cannot open device", *args)
        self.handle.claimInterface(self.interface)

    def close(self) -> None:
        if self.handle is not None:
            self.handle.releaseInterface(self.interface)
            self.handle.close()
        self.handle = None

    def write_chunk(self, chunk: bytes) -> None:
        assert self.handle is not None
        if len(chunk) != 64:
            raise TransportException("Unexpected chunk size: %d" % len(chunk))
        self.handle.interruptWrite(self.endpoint, chunk)

    def read_chunk(self) -> bytes:
        assert self.handle is not None
        endpoint = 0x80 | self.endpoint
        while True:
            chunk = self.handle.interruptRead(endpoint, 64)
            if chunk:
                break
            else:
                time.sleep(0.001)
        if len(chunk) != 64:
            raise TransportException("Unexpected chunk size: %d" % len(chunk))
        return chunk


class WebUsbTransport(ProtocolBasedTransport):
    """
    WebUsbTransport implements transport over WebUSB interface.
    """

    PATH_PREFIX = "webusb"
    ENABLED = usb1 is not None
    context = None

    def __init__(
        self, device: str, handle: WebUsbHandle = None, debug: bool = False
    ) -> None:
        if handle is None:
            handle = WebUsbHandle(device, debug)

        self.device = device
        self.handle = handle
        self.debug = debug

        super().__init__(protocol=ProtocolV1(handle))

    def get_path(self) -> str:
        return "%s:%s" % (self.PATH_PREFIX, dev_to_str(self.device))

    @classmethod
    def enumerate(cls) -> Iterable["WebUsbTransport"]:
        if cls.context is None:
            cls.context = usb1.USBContext()
            cls.context.open()
            atexit.register(cls.context.close)
        devices = []
        for dev in cls.context.getDeviceIterator(skip_on_error=True):
            usb_id = (dev.getVendorID(), dev.getProductID())
            if usb_id not in TREZORS:
                continue
            if not is_vendor_class(dev):
                continue
            try:
                # workaround for issue #223:
                # on certain combinations of Windows USB drivers and libusb versions,
                # Trezor is returned twice (possibly because Windows know it as both
                # a HID and a WebUSB device), and one of the returned devices is
                # non-functional.
                dev.getProduct()
                devices.append(WebUsbTransport(dev))
            except usb1.USBErrorNotSupported:
                pass
        return devices

    def find_debug(self) -> "WebUsbTransport":
        if self.protocol.VERSION >= 2:
            # TODO test this
            # XXX this is broken right now because sessions don't really work
            # For v2 protocol, use the same WebUSB interface with a different session
            return WebUsbTransport(self.device, self.handle)
        else:
            # For v1 protocol, find debug USB interface for the same serial number
            return WebUsbTransport(self.device, debug=True)


def is_vendor_class(dev: "usb1.USBDevice") -> bool:
    configurationId = 0
    altSettingId = 0
    return (
        dev[configurationId][INTERFACE][altSettingId].getClass()
        == usb1.libusb1.LIBUSB_CLASS_VENDOR_SPEC
    )


def dev_to_str(dev: "usb1.USBDevice") -> str:
    return ":".join(
        str(x) for x in ["%03i" % (dev.getBusNumber(),)] + dev.getPortNumberList()
    )
