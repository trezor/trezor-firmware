# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
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

from __future__ import annotations

import atexit
import logging
import sys
import time
from typing import Iterable, List

from ..log import DUMP_PACKETS
from ..models import TREZORS, TrezorModel
from . import UDEV_RULES_STR, DeviceIsBusy, Transport, TransportException

LOG = logging.getLogger(__name__)

try:
    import usb1

    USB_IMPORTED = True
except Exception as e:
    LOG.warning(f"WebUSB transport is disabled: {e}")
    USB_IMPORTED = False

INTERFACE = 0
ENDPOINT = 1
DEBUG_INTERFACE = 1
DEBUG_ENDPOINT = 2

USB_COMM_TIMEOUT_MS = 300
WEBUSB_CHUNK_SIZE = 64


class WebUsbTransport(Transport):
    """
    WebUsbTransport implements transport over WebUSB interface.
    """

    PATH_PREFIX = "webusb"
    ENABLED = USB_IMPORTED
    context = None
    CHUNK_SIZE = 64

    def __init__(
        self,
        device: "usb1.USBDevice",
        debug: bool = False,
    ) -> None:

        self.device = device
        self.debug = debug

        self.interface = DEBUG_INTERFACE if debug else INTERFACE
        self.endpoint = DEBUG_ENDPOINT if debug else ENDPOINT
        self.handle: usb1.USBDeviceHandle | None = None

        super().__init__()

    @classmethod
    def enumerate(
        cls, models: Iterable["TrezorModel"] | None = None, usb_reset: bool = False
    ) -> Iterable["WebUsbTransport"]:
        if cls.context is None:
            cls.context = usb1.USBContext()
            cls.context.open()
            atexit.register(cls.context.close)

        if models is None:
            models = TREZORS
        usb_ids = [id for model in models for id in model.usb_ids]
        devices: List["WebUsbTransport"] = []
        for dev in cls.context.getDeviceIterator(skip_on_error=True):
            usb_id = (dev.getVendorID(), dev.getProductID())
            if usb_id not in usb_ids:
                continue
            if not is_vendor_class(dev):
                continue
            if usb_reset:
                handle = dev.open()
                handle.resetDevice()
                handle.close()
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

    def get_path(self) -> str:
        return f"{self.PATH_PREFIX}:{dev_to_str(self.device)}"

    def open(self) -> None:
        self.handle = self.device.open()
        if self.handle is None:
            if sys.platform.startswith("linux"):
                args = (UDEV_RULES_STR,)
            else:
                args = ()
            raise IOError("Cannot open device", *args)
        try:
            self.handle.claimInterface(self.interface)
        except usb1.USBErrorAccess as e:
            raise DeviceIsBusy(self.device) from e
        except usb1.USBErrorBusy as e:
            raise DeviceIsBusy(self.device) from e

    def close(self) -> None:
        if self.handle is not None:
            try:
                self.handle.releaseInterface(self.interface)
                self.handle.close()
            except Exception as e:
                raise TransportException(f"USB close failed: {e}") from e
        self.handle = None

    def write_chunk(self, chunk: bytes) -> None:
        if self.handle is None:
            self.open()
        assert self.handle is not None
        if len(chunk) != WEBUSB_CHUNK_SIZE:
            raise TransportException(f"Unexpected chunk size: {len(chunk)}")
        LOG.log(DUMP_PACKETS, f"writing packet: {chunk.hex()}")
        while True:
            try:
                bytes_written = self.handle.interruptWrite(
                    self.endpoint, chunk, USB_COMM_TIMEOUT_MS
                )
            except usb1.USBErrorTimeout as e:
                bytes_written = e.transferred
            except Exception as e:
                raise TransportException(f"USB write failed: {e}") from e
            if bytes_written == 0:
                continue
            if bytes_written != len(chunk):
                raise TransportException(
                    f"USB partial write: {bytes_written} out of {WEBUSB_CHUNK_SIZE}"
                )
            return

    def read_chunk(self) -> bytes:
        if self.handle is None:
            self.open()
        assert self.handle is not None
        endpoint = 0x80 | self.endpoint
        while True:
            try:
                chunk = self.handle.interruptRead(
                    endpoint, WEBUSB_CHUNK_SIZE, USB_COMM_TIMEOUT_MS
                )
                if chunk:
                    break
                else:
                    time.sleep(0.001)
            except usb1.USBErrorTimeout:
                pass
            except Exception as e:
                raise TransportException(f"USB read failed: {e}") from e
        LOG.log(DUMP_PACKETS, f"read packet: {chunk.hex()}")
        if len(chunk) != WEBUSB_CHUNK_SIZE:
            raise TransportException(f"Unexpected chunk size: {len(chunk)}")
        return chunk

    def find_debug(self) -> "WebUsbTransport":
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
