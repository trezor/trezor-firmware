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
import logging
from queue import Queue
from typing import TYPE_CHECKING, Iterable, Optional

from .. import tealblue
from . import TransportException
from .protocol import ProtocolBasedTransport, ProtocolV1

if TYPE_CHECKING:
    from ..models import TrezorModel

LOG = logging.getLogger(__name__)

NUS_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
NUS_CHARACTERISTIC_RX = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
NUS_CHARACTERISTIC_TX = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"


def scan_device(adapter, devices):
    with adapter.scan(2) as scanner:
        for device in scanner:
            if NUS_SERVICE_UUID in device.UUIDs:
                if device.address not in [d.address for d in devices]:
                    print(f"Found device: {device.name}, {device.address}")
                    devices.append(device)
    return devices


def lookup_device(adapter):
    devices = []
    for device in adapter.devices():
        if NUS_SERVICE_UUID in device.UUIDs:
            devices.append(device)
    return devices


class BleTransport(ProtocolBasedTransport):
    ENABLED = True
    PATH_PREFIX = "ble"

    def __init__(self, mac_addr: str, adapter) -> None:

        self.tx = None
        self.rx = None
        self.device = mac_addr
        self.adapter = adapter
        self.received_data = Queue()

        devices = lookup_device(self.adapter)

        for d in devices:
            if d.address == mac_addr:
                self.ble_device = d
                break

        super().__init__(protocol=ProtocolV1(self))

    def get_path(self) -> str:
        return "{}:{}".format(self.PATH_PREFIX, self.device)

    def find_debug(self) -> "BleTransport":
        mac = self.device
        return BleTransport(f"{mac}")

    @classmethod
    def enumerate(
        cls, _models: Optional[Iterable["TrezorModel"]] = None
    ) -> Iterable["BleTransport"]:
        adapter = tealblue.TealBlue().find_adapter()
        devices = lookup_device(adapter)

        devices = [d for d in devices if d.connected]

        if len(devices) == 0:
            print("Scanning...")
            devices = scan_device(adapter, devices)

        print("Found %d devices" % len(devices))

        for device in devices:
            print(f"Device: {device.name}, {device.address}")

        return [BleTransport(device.address, adapter) for device in devices]

    # @classmethod
    # def find_by_path(cls, path: str, prefix_search: bool = False) -> "BleTransport":
    #     try:
    #         path = path.replace(f"{cls.PATH_PREFIX}:", "")
    #         return cls._try_path(path)
    #     except TransportException:
    #         if not prefix_search:
    #             raise
    #
    #     if prefix_search:
    #         return super().find_by_path(path, prefix_search)
    #     else:
    #         raise TransportException(f"No UDP device at {path}")

    def open(self) -> None:

        if not self.ble_device.connected:
            print(
                "Connecting to %s (%s)..."
                % (self.ble_device.name, self.ble_device.address)
            )
            self.ble_device.connect()
        else:
            print(
                "Connected to %s (%s)."
                % (self.ble_device.name, self.ble_device.address)
            )

        if not self.ble_device.services_resolved:
            print("Resolving services...")
            self.ble_device.resolve_services()

        service = self.ble_device.services[NUS_SERVICE_UUID]
        self.rx = service.characteristics[NUS_CHARACTERISTIC_RX]
        self.tx = service.characteristics[NUS_CHARACTERISTIC_TX]

        def on_notify(characteristic, value):
            self.received_data.put(bytes(value))

        self.tx.on_notify = on_notify
        self.tx.start_notify()

    def close(self) -> None:
        pass

    def write_chunk(self, chunk: bytes) -> None:
        assert self.rx is not None
        self.rx.write(chunk)

    def read_chunk(self) -> bytes:
        assert self.tx is not None
        chunk = self.received_data.get()
        # LOG.log(DUMP_PACKETS, f"received packet: {chunk.hex()}")
        if len(chunk) != 64:
            raise TransportException(f"Unexpected chunk size: {len(chunk)}")
        return bytearray(chunk)
