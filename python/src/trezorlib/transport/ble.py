# This file is part of the Trezor project.
#
# Copyright (C) 2012-2025 SatoshiLabs and contributors
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
import atexit
import logging
from dataclasses import dataclass
from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection
from typing import TYPE_CHECKING, Any, Iterable, Optional

from . import Timeout, TransportException
from .protocol import ProtocolBasedTransport, ProtocolV1

if TYPE_CHECKING:
    from ..models import TrezorModel

LOG = logging.getLogger(__name__)

TREZOR_SERVICE_UUID = "8c000001-a59b-4d58-a9ad-073df69fa1b1"
TREZOR_CHARACTERISTIC_RX = "8c000002-a59b-4d58-a9ad-073df69fa1b1"
TREZOR_CHARACTERISTIC_TX = "8c000003-a59b-4d58-a9ad-073df69fa1b1"



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
        return BleTransport(self.device)  # FIXME WebUsb

    @classmethod
    def enumerate(
        cls, _models: Optional[Iterable["TrezorModel"]] = None  # FIXME models
    ) -> Iterable["BleTransport"]:
        devices = cls.ble().scan()
        # FIXME we're dropping the name here
        return [BleTransport(device[0]) for device in devices]

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
        pass  # self.ble().disconnect()

    def write_chunk(self, chunk: bytes) -> None:
        self.ble().write(self.device, chunk)

    def read_chunk(self, timeout: Optional[float] = None) -> bytes:
        chunk = self.ble().read(self.device, timeout)
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

        atexit.register(self._shutdown)

    def __getattr__(self, name: str):
        def f(*args: Any, **kwargs: Any):
            assert self.pipe is not None
            self.pipe.send((name, args, kwargs))
            result = self.pipe.recv()
            if isinstance(result, BaseException):
                raise result
            return result

        return f

    def _shutdown(self):
        self.pipe.send(("shutdown", [], {}))
        self.process.join(10)  # is timeout


class BleAsync:
    class Shutdown(Exception):
        pass

#    @dataclass
#    class Peripheral:
#        device = None
#        adv_data = None
#        client = None
#        queue = None

    def __init__(self, pipe: Connection):
        asyncio.run(self.main(pipe))

    async def main(self, pipe: Connection):
        self.connected = {}

        # TODO: currently only one concurrent device is supported
        self.current = None
        self.devices = {}
        self.queue = asyncio.Queue()
        self.scanned = None
        LOG.debug("async BLE process started")
        # TODO: signal ready to main process?

        while True:
            await ready(pipe)
            cmd, args, kwargs = pipe.recv()
            try:
                result = await getattr(self, cmd)(*args, **kwargs)
            except self.Shutdown:
                LOG.debug("async BLE exit loop")
                break
            except Timeout as e:
                await ready(pipe, write=True)
                pipe.send(e)
            except Exception as e:
                LOG.exception("Error in async BLE process:")
                await ready(pipe, write=True)
                pipe.send(e)
                break
            else:
                await ready(pipe, write=True)
                pipe.send(result)

        await self.disconnect("FIXME")  # TODO foreach

    async def scan(self) -> list[tuple[str, str]]:
        LOG.debug("scanning BLE")

        from bleak import BleakScanner

        # NOTE BleakScanner.discover(service_uuids=[TREZOR_SERVICE_UUID]) is broken
        # problem possibly on the bluez side

        devices = await BleakScanner.discover(
            timeout=3,
            return_adv=True,
        )

        self.scanned = []
        res = []
        for address, (dev, adv_data) in devices.items():
            if TREZOR_SERVICE_UUID not in adv_data.service_uuids:
                continue
            LOG.debug(f"scan: {dev.address}: {dev.name} rssi={adv_data.rssi} manufacturer_data={adv_data.manufacturer_data}")
            self.scanned.append(dev)
            res.append((dev.address, dev.name))  # FIXME
        return res

    async def connect(self, address: str):

        from bleak import BleakClient

        # already connected?
        # scanned?
        # connect by addr
        if self.current and self.current.address == address:
            return

        ble_device = self.devices.get(address)
        if ble_device:
            LOG.debug(f"Already connected to {ble_device.address}")
            self.current = ble_device
            return

        if self.scanned is None:
            await self.scan()

        for dev in self.scanned:
            if dev.address == address:
                break
        else:
            raise RuntimeError("device not found")

        LOG.debug(f"Connecting to {address}...")
        ble_device = BleakClient(dev)  # TODO: services, timeout
        await ble_device.connect()
        self.current = ble_device

        # import subprocess
        # subprocess.run("gnome-control-center bluetooth")

        await ble_device.pair()
        self.devices[address] = ble_device

        async def read_callback(characteristic, data):
            await self.queue.put(data)

        await ble_device.start_notify(TREZOR_CHARACTERISTIC_TX, read_callback)
        LOG.info(f"Connected to {ble_device.address}")

    async def disconnect(self, address: str):
        if self.current is None:
            return
        ble_device = self.current
        await ble_device.stop_notify(TREZOR_CHARACTERISTIC_TX)
        await ble_device.disconnect()  # throws EOFError sometimes
        LOG.info(f"Disconnected from {ble_device.address}")
        self.current = None

    async def read(self, address: str, timeout: float | None):
        assert self.current
        try:
            return await asyncio.wait_for(self.queue.get(), timeout=timeout)
        except (TimeoutError, asyncio.TimeoutError):
            raise Timeout(f"Timeout reading BLE packet ({timeout}s)")

    async def write(self, address: str, chunk: bytes):
        assert self.current
        await self.current.write_gatt_char(TREZOR_CHARACTERISTIC_RX, chunk, response=False)

    async def shutdown(self):
        raise self.Shutdown


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
