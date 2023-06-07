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
import asyncio
import logging
from dataclasses import dataclass
from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection
from typing import TYPE_CHECKING, Any, Iterable, List, Optional

from . import TransportException
from .protocol import ProtocolBasedTransport, ProtocolV1

if TYPE_CHECKING:
    from ..models import TrezorModel

LOG = logging.getLogger(__name__)

NUS_SERVICE_UUID = "8c000001-a59b-4d58-a9ad-073df69fa1b1"
NUS_CHARACTERISTIC_RX = "8c000002-a59b-4d58-a9ad-073df69fa1b1"
NUS_CHARACTERISTIC_TX = "8c000003-a59b-4d58-a9ad-073df69fa1b1"


@dataclass
class Device:
    address: str
    name: str
    connected: bool


class BleTransport(ProtocolBasedTransport):
    ENABLED = True
    PATH_PREFIX = "ble"

    _ble = None

    def __init__(self, mac_addr: str) -> None:
        self.device = mac_addr
        super().__init__(protocol=ProtocolV1(self, replen=244))

    def get_path(self) -> str:
        return "{}:{}".format(self.PATH_PREFIX, self.device)

    def find_debug(self) -> "BleTransport":
        return BleTransport(self.device)

    @classmethod
    def enumerate(
        cls, _models: Optional[Iterable["TrezorModel"]] = None
    ) -> Iterable["BleTransport"]:
        devices = cls.ble().lookup()
        return [BleTransport(device.address) for device in devices if device.connected]

    @classmethod
    def _try_path(cls, path: str) -> "BleTransport":
        devices = cls.enumerate(None)
        devices = [d for d in devices if d.device == path]
        if len(devices) == 0:
            raise TransportException(f"No BLE device: {path}")
        return devices[0]

    @classmethod
    def find_by_path(cls, path: str, prefix_search: bool = False) -> "BleTransport":
        if not prefix_search:
            raise TransportException

        if prefix_search:
            return super().find_by_path(path, prefix_search)
        else:
            raise TransportException(f"No BLE device: {path}")

    def open(self) -> None:
        self.ble().connect(self.device)

    def close(self) -> None:
        pass

    def write_chunk(self, chunk: bytes) -> None:
        self.ble().write(chunk)

    def read_chunk(self) -> bytes:
        chunk = self.ble().read()
        # LOG.log(DUMP_PACKETS, f"received packet: {chunk.hex()}")
        if len(chunk) != 64:
            raise TransportException(f"Unexpected chunk size: {len(chunk)}")
        return bytearray(chunk)

    @classmethod
    def ble(cls) -> "BleProxy":
        if cls._ble is None:
            cls._ble = BleProxy()
        return cls._ble


class BleProxy:
    pipe = None
    process = None

    def __init__(self):
        if self.pipe is not None:
            return

        parent_pipe, child_pipe = Pipe()
        self.pipe = parent_pipe
        self.process = Process(target=BleAsync, args=(child_pipe,), daemon=True)
        self.process.start()

    def __getattr__(self, name: str):
        def f(*args: Any, **kwargs: Any):
            assert self.pipe is not None
            self.pipe.send((name, args, kwargs))
            result = self.pipe.recv()
            if isinstance(result, BaseException):
                raise result
            return result

        return f


class BleAsync:
    def __init__(self, pipe: Connection):
        asyncio.run(self.main(pipe))

    async def main(self, pipe: Connection):
        from ..tealblue import TealBlue

        tb = await TealBlue.create()
        # TODO: add cli option for mac_filter and pass it here
        self.adapter = await tb.find_adapter()
        # TODO: currently only  one concurrent device is supported
        #   To support more devices, connect() needs to return a Connection and also has to
        #   spawn a task that will forward data between that Connection and rx,tx.
        self.current = None
        self.rx = None
        self.tx = None

        self.devices = {}
        await self.lookup()  # populate self.devices
        LOG.debug("async BLE process started")

        while True:
            await ready(pipe)
            cmd, args, kwargs = pipe.recv()
            try:
                result = await getattr(self, cmd)(*args, **kwargs)
            except Exception as e:
                LOG.exception("Error in async BLE process:")
                await ready(pipe, write=True)
                pipe.send(e)
                break
            else:
                await ready(pipe, write=True)
                pipe.send(result)

    async def lookup(self) -> List[Device]:
        self.devices.clear()
        for device in await self.adapter.devices():
            if NUS_SERVICE_UUID in device.UUIDs:
                self.devices[device.address] = device
        return [
            Device(device.address, device.name, device.connected)
            for device in self.devices.values()
        ]

    async def scan(self) -> List[Device]:
        LOG.debug("Initiating scan")
        # TODO: configurable timeout
        scanner = await self.adapter.scan(2)
        self.devices.clear()
        async with scanner:
            async for device in scanner:
                if NUS_SERVICE_UUID in device.UUIDs:
                    if device.address not in self.devices:
                        LOG.debug(f"scan: {device.address}: {device.name}")
                        self.devices[device.address] = device
        return [
            Device(device.address, device.name, device.connected)
            for device in self.devices.values()
        ]

    async def connect(self, address: str):
        if self.current == address:
            return
        # elif self.current is not None:
        #     self.devices[self.current].disconnect()

        ble_device = self.devices[address]
        if not ble_device.connected:
            LOG.info("Connecting to %s (%s)..." % (ble_device.name, ble_device.address))
            await ble_device.connect()
        else:
            LOG.info("Connected to %s (%s)." % (ble_device.name, ble_device.address))

        services = await ble_device.services()
        nus_service = services[NUS_SERVICE_UUID]
        self.rx, _mtu = await nus_service.characteristics[
            NUS_CHARACTERISTIC_RX
        ].acquire(write=True)
        self.tx, _mtu = await nus_service.characteristics[
            NUS_CHARACTERISTIC_TX
        ].acquire()
        self.current = address

    async def disconnect(self):
        if self.current is None:
            return
        ble_device = self.devices[self.current]
        if ble_device.connected:
            LOG.info(
                "Disconnecting from %s (%s)..." % (ble_device.name, ble_device.address)
            )
            await ble_device.disconnect()
        else:
            LOG.info(
                "Disconnected from %s (%s)." % (ble_device.name, ble_device.address)
            )
        self.current = None
        self.rx = None
        self.tx = None

    async def read(self):
        assert self.tx is not None
        await ready(self.tx)
        return self.tx.read()

    async def write(self, chunk: bytes):
        assert self.rx is not None
        await ready(self.rx, write=True)
        self.rx.write(chunk)


async def ready(f: Any, write: bool = False):
    """Asynchronously wait for file-like object to become ready for reading or writing."""
    fd = f.fileno()
    loop = asyncio.get_event_loop()
    event = asyncio.Event()

    if write:

        def callback():
            event.set()
            loop.remove_writer(fd)

        loop.add_writer(fd, callback)
    else:

        def callback():
            event.set()
            loop.remove_reader(fd)

        loop.add_reader(fd, callback)

    await event.wait()
