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
from __future__ import annotations

import asyncio
import atexit
import logging
import typing as t
from dataclasses import dataclass
from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection

from ..log import DUMP_PACKETS
from ..models import T3W1
from . import Timeout, Transport, TransportException
from .udp import UdpTransport

if t.TYPE_CHECKING:
    from ..models import TrezorModel

try:
    from bleak import BleakClient, BleakScanner
    from bleak.backends.characteristic import BleakGATTCharacteristic
    from bleak.backends.device import BLEDevice
    from bleak.backends.scanner import AdvertisementData
    from bleak.exc import BleakError

    BLEAK_IMPORTED = True
except ImportError:
    BLEAK_IMPORTED = False

LOG = logging.getLogger(__name__)

TREZOR_SERVICE_UUID = "8c000001-a59b-4d58-a9ad-073df69fa1b1"
TREZOR_CHARACTERISTIC_RX = "8c000002-a59b-4d58-a9ad-073df69fa1b1"
TREZOR_CHARACTERISTIC_TX = "8c000003-a59b-4d58-a9ad-073df69fa1b1"

SCAN_INTERVAL_SECONDS = 3
SHUTDOWN_TIMEOUT_SECONDS = 10


class BleTransport(Transport):
    ENABLED = True
    PATH_PREFIX = "ble"
    CHUNK_SIZE = 244

    _ble = None

    def __init__(self, address: str) -> None:
        self.device = address
        super().__init__()

    def get_path(self) -> str:
        return "{}:{}".format(self.PATH_PREFIX, self.device)

    def find_debug(self) -> UdpTransport:
        return UdpTransport("127.0.0.1:27315")

    @classmethod
    def enumerate(
        cls, models: t.Iterable[TrezorModel] | None = None
    ) -> t.Iterable[BleTransport]:
        # TODO use manufacturer_data
        if models and T3W1 not in models:
            return []
        devices = cls.ble_proxy().scan()
        return [BleTransport(device[0]) for device in devices]

    @classmethod
    def _try_path(cls, path: str) -> BleTransport:
        devices = cls.enumerate(None)
        devices = [d for d in devices if d.device == path]
        if len(devices) == 0:
            raise TransportException(f"No BLE device: {path}")
        return devices[0]

    @classmethod
    def find_by_path(cls, path: str, prefix_search: bool = False) -> BleTransport:
        if not prefix_search:
            raise TransportException

        if prefix_search:
            return super().find_by_path(path, prefix_search)
        else:
            raise TransportException(f"No BLE device: {path}")

    def open(self) -> None:
        self.ble_proxy().connect(self.device)

    def close(self) -> None:
        # would be a logical place to call self.ble_proxy().disconnect()
        # instead we rely on atexit handler to avoid reconnecting
        pass

    def write_chunk(self, chunk: bytes) -> None:
        LOG.log(DUMP_PACKETS, f"sending packet: {chunk.hex()}")
        self.ble_proxy().write(self.device, chunk)

    def read_chunk(self, timeout: float | None = None) -> bytes:
        chunk = self.ble_proxy().read(self.device, timeout)
        LOG.log(DUMP_PACKETS, f"received packet: {chunk.hex()}")
        if len(chunk) not in (64, 244):
            LOG.error(f"{__name__}: unexpected chunk size: {len(chunk)}")
        return bytes(chunk)

    @classmethod
    def ble_proxy(cls) -> BleProxy:
        if cls._ble is None:
            cls._ble = BleProxy()
        return cls._ble


class BleProxy:
    pipe: Connection[t.Any, t.Any] | None = None
    process: Process | None = None

    def __init__(self) -> None:
        if not BLEAK_IMPORTED:
            raise RuntimeError("Bleak library not available, BLE support disabled")

        if self.pipe is not None:
            return

        parent_pipe, child_pipe = Pipe()
        self.pipe = parent_pipe
        self.process = Process(target=BleAsync, args=(child_pipe,), daemon=True)
        self.process.start()

        atexit.register(self._shutdown)

    def __getattr__(self, name: str) -> t.Callable[..., t.Any]:
        def f(*args: t.Any, **kwargs: t.Any) -> t.Any:
            assert self.pipe is not None
            self.pipe.send((name, args, kwargs))
            result = self.pipe.recv()
            if isinstance(result, BaseException):
                raise result
            return result

        return f

    def _shutdown(self) -> None:
        if self.pipe is not None:
            try:
                self.pipe.send(("shutdown", [], {}))
            except BrokenPipeError:
                LOG.debug(f"{__name__}: broken pipe")
            self.pipe = None
        if self.process is not None:
            self.process.join(SHUTDOWN_TIMEOUT_SECONDS)
            self.process = None


@dataclass
class Peripheral:
    device: BLEDevice
    adv_data: AdvertisementData
    client: BleakClient | None = None
    queue: asyncio.Queue | None = None

    @property
    def address(self) -> str:
        return self.device.address


class BleAsync:
    class Shutdown(Exception):
        pass

    def __init__(self, pipe: Connection) -> None:
        asyncio.run(self.main(pipe))

    async def main(self, pipe: Connection) -> None:
        self.devices = {}
        self.did_scan = False
        LOG.debug("async BLE process started")

        try:
            await self._main_loop(pipe)
        finally:
            for address in self.devices.keys():
                await self.disconnect(address)

    # returns after shutdown, or raises an exception
    async def _main_loop(self, pipe: Connection) -> None:
        while True:
            await ready(pipe)
            cmd, args, kwargs = pipe.recv()
            try:
                result = await getattr(self, cmd)(*args, **kwargs)
            except self.Shutdown:
                LOG.debug("async BLE exit loop")
                return
            except Timeout as e:
                await ready(pipe, write=True)
                pipe.send(e)
            except Exception as e:
                LOG.exception("Error in async BLE process:")
                await ready(pipe, write=True)
                pipe.send(e)
            else:
                await ready(pipe, write=True)
                pipe.send(result)

    # throws exception when no adapters found
    async def scan(self) -> list[tuple[str, str]]:
        LOG.debug("scanning BLE")

        # NOTE BleakScanner.discover(service_uuids=[TREZOR_SERVICE_UUID]) is broken
        # problem possibly on the bluez side

        devices = await BleakScanner.discover(
            timeout=SCAN_INTERVAL_SECONDS,
            return_adv=True,
        )

        # throw away non connected peripherals
        self.devices = {
            addr: periph for addr, periph in self.devices.values() if periph.client
        }
        for address, (dev, adv_data) in devices.items():
            if TREZOR_SERVICE_UUID not in adv_data.service_uuids:
                continue
            LOG.debug(
                f"scan: {dev.address}: {dev.name} rssi={adv_data.rssi} manufacturer_data={adv_data.manufacturer_data}"
            )
            if address in self.devices:
                self.devices[address].device = dev
                self.devices[address].adv_data = adv_data
            else:
                self.devices[address] = Peripheral(dev, adv_data)
        self.did_scan = True
        return [
            (periph.address, periph.device.name) for periph in self.devices.values()
        ]

    async def connect(self, address: str) -> None:
        if not self.did_scan:
            await self.scan()

        periph = self.devices.get(address)
        if not periph:
            raise RuntimeError("device not found")

        if periph.client:
            LOG.debug(f"Already connected to {periph.address}")
            return

        async def disconnect_callback(client: BleakClient) -> None:
            LOG.error(f"Got disconnected from {periph.address}")
            self.devices[address].client = None
            self.devices[address].queue = None

        LOG.debug(f"Connecting to {address}...")
        client = BleakClient(
            periph.device,
            services=[TREZOR_SERVICE_UUID],
            timeout=SCAN_INTERVAL_SECONDS,
            disconnect_callback=disconnect_callback,
        )
        await client.connect()

        # here we should set up the pairing agent
        # https://github.com/hbldh/bleak/pull/1100
        # or do what Suite does and try to launch some native gui
        # import subprocess
        # subprocess.Popen("gnome-control-center bluetooth", shell=True)

        # if there is no pairing agent we get (on linux)
        # bleak.exc.BleakDBusError: [org.bluez.Error.AuthenticationFailed] Authentication Failed
        try:
            await client.pair()
        except BleakError:
            LOG.error("BLE pairing failed - make sure to open system pairing dialog")
            raise

        queue = asyncio.Queue()

        async def read_callback(
            characteristic: BleakGATTCharacteristic, data: bytearray
        ) -> None:
            await queue.put(data)

        await client.start_notify(TREZOR_CHARACTERISTIC_TX, read_callback)
        periph.client = client
        periph.queue = queue
        LOG.info(f"Connected to {client.address}")

    async def disconnect(self, address: str) -> None:
        periph = self.devices.get(address)
        if not periph or not periph.client:
            return

        try:
            await periph.client.stop_notify(TREZOR_CHARACTERISTIC_TX)
            await periph.client.disconnect()
            LOG.info(f"Disconnected from {periph.address}")
        except EOFError:
            LOG.debug(f"EOF when disconnecting from {periph.address}")
        except Exception as ex:
            LOG.error(f"Failed to disconnect from {periph.address}")
            LOG.exception(ex)
        finally:
            periph.client = None
            periph.queue = None

    async def read(self, address: str, timeout: float | None) -> bytes:
        periph = self.devices[address]
        try:
            return await asyncio.wait_for(periph.queue.get(), timeout=timeout)
        except (TimeoutError, asyncio.TimeoutError):
            raise Timeout(f"Timeout reading BLE packet ({timeout}s)")

    async def write(self, address: str, chunk: bytes) -> None:
        periph = self.devices[address]
        await periph.client.write_gatt_char(
            TREZOR_CHARACTERISTIC_RX, chunk, response=False
        )

    async def shutdown(self) -> None:
        raise self.Shutdown


async def ready(f: Connection, write: bool = False) -> None:
    """Asynchronously wait for file-like object to become ready for reading or writing."""
    fd = f.fileno()
    loop = asyncio.get_event_loop()
    event = asyncio.Event()

    if write:

        def callback() -> None:
            event.set()
            loop.remove_writer(fd)

        loop.add_writer(fd, callback)
    else:

        def callback() -> None:
            event.set()
            loop.remove_reader(fd)

        loop.add_reader(fd, callback)

    await event.wait()
