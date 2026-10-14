# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
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
import sys
import typing as t
from dataclasses import dataclass
from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection

from ..log import DUMP_PACKETS
from . import Timeout, Transport, TransportException

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

# Debuglink over BLE: a separate service on debug firmware with a debug nRF
# image, the counterpart of the USB debug interface. Same connection as the
# wire service, so both are driven from the one bleak client.
TREZOR_DEBUG_SERVICE_UUID = "8c000020-a59b-4d58-a9ad-073df69fa1b1"
TREZOR_DEBUG_CHARACTERISTIC_RX = "8c000021-a59b-4d58-a9ad-073df69fa1b1"
TREZOR_DEBUG_CHARACTERISTIC_TX = "8c000022-a59b-4d58-a9ad-073df69fa1b1"

SCAN_INTERVAL_SECONDS = 3
# Establishing the connection can take a few advertising intervals plus the
# encryption setup; the scan interval is too short for that.
CONNECT_TIMEOUT_SECONDS = 15
SHUTDOWN_TIMEOUT_SECONDS = 10

SHOULD_WRITE_WITH_RESPONSE = sys.platform == "darwin"


class BleTransport(Transport):
    ENABLED = BLEAK_IMPORTED
    PATH_PREFIX = "ble"
    CHUNK_SIZE = 244

    _ble = None

    def __init__(self, address: str) -> None:
        self.device = address
        super().__init__()

    def get_path(self) -> str:
        return "{}:{}".format(self.PATH_PREFIX, self.device)

    def find_debug(self) -> BleDebugTransport:
        # The services are only known once connected; connecting here is what
        # open() does anyway and the proxy keeps the one connection.
        proxy = self.ble_proxy()
        if not proxy.is_connected(self.device):
            proxy.connect(self.device)
        if not proxy.has_debug(self.device):
            raise TransportException(
                f"{self.get_path()} has no debuglink service "
                "(needs debug firmware and a debug nRF image)"
            )
        return BleDebugTransport(self.device)

    @classmethod
    def enumerate(
        cls, models: t.Iterable[TrezorModel] | None = None
    ) -> t.Iterable[BleTransport]:
        # TODO use manufacturer_data
        # Skip BLE enumeration unless at least one requested model is BLE-capable
        # (capability comes from the single-source model registry).
        if models and not any(model.ble_capable for model in models):
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
        try:
            return super().find_by_path(path, prefix_search)
        except TransportException:
            # A full address needs no scan to be useful: a device the system
            # is already connected to (another tool holds the link) does not
            # advertise, and connect() can still attach to it on Linux.
            address = path[len(cls.PATH_PREFIX) + 1 :]
            if len(address.split(":")) == 6 and all(
                len(octet) == 2 for octet in address.split(":")
            ):
                return cls(address.upper())
            raise

    def _open(self) -> None:
        self.ble_proxy().connect(self.device)

    def _close(self) -> None:
        # would be a logical place to call self.ble_proxy().disconnect()
        # instead we rely on atexit handler to avoid reconnecting
        pass

    def is_open(self) -> bool:
        return self.ble_proxy().is_connected(self.device)

    # which characteristic pair the chunks go through
    DEBUG = False

    def write_chunk(self, chunk: bytes) -> None:
        LOG.log(DUMP_PACKETS, f"sending packet: {chunk.hex()}")
        self.ble_proxy().write(self.device, chunk, self.DEBUG)

    def read_chunk(self, timeout: float | None = None) -> bytes:
        chunk = self.ble_proxy().read(self.device, timeout, self.DEBUG)
        LOG.log(DUMP_PACKETS, f"received packet: {chunk.hex()}")
        if len(chunk) not in (64, 244):
            LOG.error(f"{__name__}: unexpected chunk size: {len(chunk)}")
        return bytes(chunk)

    @classmethod
    def ble_proxy(cls) -> BleProxy:
        if cls._ble is None:
            cls._ble = BleProxy()
        return cls._ble

    def is_ready(self) -> bool:
        return self._ble is not None


class BleDebugTransport(BleTransport):
    """The debuglink of a BLE device, on the device's debug service.

    Obtained through `BleTransport.find_debug()`; shares the wire transport's
    connection and bond, only the characteristics differ. The device sends
    and expects whole 244-byte codec v1 reports, which is this transport's
    chunk size already.
    """

    PATH_PREFIX = "ble-debug"
    DEBUG = True

    @classmethod
    def enumerate(
        cls, models: t.Iterable[TrezorModel] | None = None
    ) -> t.Iterable[BleDebugTransport]:
        # Never a device of its own; reached through find_debug() only.
        return []

    def find_debug(self) -> BleDebugTransport:
        return self


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
    # debuglink service, present on debug firmware with a debug nRF image
    debug_queue: asyncio.Queue | None = None

    @property
    def address(self) -> str:
        return self.device.address


class BleAsync:
    class Shutdown(Exception):
        pass

    def __init__(self, pipe: Connection) -> None:
        asyncio.run(self.main(pipe))

    async def main(self, pipe: Connection) -> None:
        self.devices: dict[str, Peripheral] = {}
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
            addr: periph for addr, periph in self.devices.items() if periph.client
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
            (periph.address, periph.device.name)
            for periph in self.devices.values()
            if periph.device.name is not None
        ]

    async def connect(self, address: str) -> None:
        if not self.did_scan:
            await self.scan()

        periph = self.devices.get(address)
        if not periph:
            periph = await self._known_to_system(address)
        if not periph:
            raise RuntimeError(f"Device not found: {address}")

        if periph.client:
            LOG.debug(f"Already connected to {periph.address}")
            return

        async def disconnect_callback(client: BleakClient) -> None:
            LOG.error(f"Got disconnected from {periph.address}")
            self.devices[address].client = None
            self.devices[address].queue = None
            self.devices[address].debug_queue = None

        LOG.debug(f"Connecting to {address}...")
        client = BleakClient(
            periph.device,
            services=[TREZOR_SERVICE_UUID, TREZOR_DEBUG_SERVICE_UUID],
            timeout=CONNECT_TIMEOUT_SECONDS,
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
        except NotImplementedError:
            # expected on macOS
            if sys.platform != "darwin":
                LOG.warning(
                    "Failed to initiate pairing. You may need to pair the device manually."
                )

        queue = asyncio.Queue()

        async def read_callback(
            characteristic: BleakGATTCharacteristic, data: bytearray
        ) -> None:
            await queue.put(data)

        await client.start_notify(TREZOR_CHARACTERISTIC_TX, read_callback)

        debug_queue = None
        if client.services.get_characteristic(TREZOR_DEBUG_CHARACTERISTIC_TX):
            debug_queue = asyncio.Queue()

            async def debug_read_callback(
                characteristic: BleakGATTCharacteristic, data: bytearray
            ) -> None:
                await debug_queue.put(data)

            await client.start_notify(
                TREZOR_DEBUG_CHARACTERISTIC_TX, debug_read_callback
            )
            LOG.debug(f"Debuglink service present on {client.address}")

        periph.client = client
        periph.queue = queue
        periph.debug_queue = debug_queue
        LOG.info(f"Connected to {client.address}")

    async def _known_to_system(self, address: str) -> Peripheral | None:
        """A device BlueZ already has, typically connected by another tool and
        therefore not advertising. bleak attaches to it by its D-Bus path
        without a scan; the path is BlueZ's and is looked up by address, as it
        keeps the address the device was first seen under. Linux only."""
        if sys.platform != "linux":
            return None
        from bleak.backends.bluezdbus.manager import get_global_bluez_manager

        manager = await get_global_bluez_manager()
        for path, props in manager._properties.items():
            dev = props.get("org.bluez.Device1")
            if not dev or dev.get("Address", "").upper() != address.upper():
                continue
            LOG.debug(f"{address} not seen advertising, using BlueZ object {path}")
            device = BLEDevice(
                address.upper(), dev.get("Name"), {"path": path, "props": dev}
            )
            adv = AdvertisementData(
                dev.get("Name"), {}, {}, list(dev.get("UUIDs", [])), None, -127, ()
            )
            periph = Peripheral(device, adv)
            self.devices[address] = periph
            return periph
        return None

    async def is_connected(self, address: str) -> bool:
        periph = self.devices.get(address)
        if not periph:
            return False
        return bool(periph.client)

    async def has_debug(self, address: str) -> bool:
        periph = self.devices.get(address)
        if not periph or not periph.client:
            return False
        return periph.debug_queue is not None

    async def disconnect(self, address: str) -> None:
        periph = self.devices.get(address)
        if not periph or not periph.client:
            return

        try:
            await periph.client.stop_notify(TREZOR_CHARACTERISTIC_TX)
            if periph.debug_queue is not None:
                await periph.client.stop_notify(TREZOR_DEBUG_CHARACTERISTIC_TX)
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
            periph.debug_queue = None

    async def read(
        self, address: str, timeout: float | None, debug: bool = False
    ) -> bytes:
        periph = self.devices[address]
        queue = periph.debug_queue if debug else periph.queue
        if queue is None:
            raise RuntimeError("Connect to peripheral before reading")
        try:
            return await asyncio.wait_for(queue.get(), timeout=timeout)
        except (TimeoutError, asyncio.TimeoutError) as err:
            raise Timeout(f"Timeout reading BLE packet ({timeout}s)") from err

    async def write(self, address: str, chunk: bytes, debug: bool = False) -> None:
        periph = self.devices[address]
        if periph.client is None:
            raise RuntimeError("Connect to peripheral before writing")
        if debug and periph.debug_queue is None:
            raise RuntimeError("Peripheral has no debuglink service")
        char = TREZOR_DEBUG_CHARACTERISTIC_RX if debug else TREZOR_CHARACTERISTIC_RX
        await periph.client.write_gatt_char(
            char, chunk, response=SHOULD_WRITE_WITH_RESPONSE
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
