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

NUS_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
NUS_CHARACTERISTIC_RX = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
NUS_CHARACTERISTIC_TX = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"


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
        self.conn = self.ble().connect(self.device)

    def close(self) -> None:
        # self.ble().disconnect(self.device)
        self.conn = None

    def write_chunk(self, chunk: bytes) -> None:
        self.conn.send(chunk)

    def read_chunk(self) -> bytes:
        chunk = self.conn.recv()
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
        self.connected = {}

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
        if address in self.connected:
            return self.connected[address][0]
            # raise RuntimeError("Already connected")

        ble_device = self.devices[address]
        if not ble_device.connected:
            LOG.info("Connecting to %s (%s)..." % (ble_device.name, ble_device.address))
            await ble_device.connect()
        else:
            LOG.info("Connected to %s (%s)." % (ble_device.name, ble_device.address))

        services = await ble_device.services()
        nus_service = services[NUS_SERVICE_UUID]
        rx, _mtu = await nus_service.characteristics[NUS_CHARACTERISTIC_RX].acquire(
            write=True
        )
        tx, _mtu = await nus_service.characteristics[NUS_CHARACTERISTIC_TX].acquire()

        parent_pipe, child_pipe = Pipe()

        async def reader():
            while True:
                await ready(tx)
                val = tx.read(64)
                await ready(child_pipe, write=True)
                child_pipe.send(val)

        async def writer():
            while True:
                await ready(child_pipe)
                val = child_pipe.recv()
                await ready(rx, write=True)
                rx.write(val)

        task_r = asyncio.create_task(reader())
        task_w = asyncio.create_task(writer())
        self.connected[address] = (parent_pipe, rx, tx, task_r, task_w)

        return parent_pipe

    async def disconnect(self, address: str):
        if address not in self.connected:
            return

        # (pipe, rx, tx, task_r, task_w) = self.connected[address]
        # rx.close()
        # tx.close()
        # pipe.close()
        # task_r.cancel()
        # task_w.cancel()
        # del self.connected[address]


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
