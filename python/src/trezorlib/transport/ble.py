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
import sys
import time
import typing as t
from dataclasses import dataclass
from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection

from .. import log
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

SCAN_INTERVAL_SECONDS = 5
CONNECT_TIMEOUT_SECONDS = 30
SCAN_LINGER_SECONDS = 2 * CONNECT_TIMEOUT_SECONDS
SHUTDOWN_TIMEOUT_SECONDS = 10

SHOULD_WRITE_WITH_RESPONSE = sys.platform == "darwin"

if sys.platform == "darwin":
    _FULL_LEN = len("ble:00000000-0000-0000-0000-000000000000")
else:
    _FULL_LEN = len("ble:00:00:00:00:00:00")


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

    @classmethod
    def find_by_path(cls, path: str, prefix_search: bool = False) -> "BleTransport":
        # short circuit non-prefix search
        # full-len path should probably avoid scanning and use BleakScanner.find_device_by_address
        if not prefix_search and len(path) != _FULL_LEN:
            raise TransportException(f"BLE device not found: {path}")
        return super().find_by_path(path, prefix_search)

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

    def _open(self) -> None:
        self.ble_proxy().connect(self.device)

    def _close(self) -> None:
        # would be a logical place to call self.ble_proxy().disconnect()
        # instead we rely on atexit handler to avoid reconnecting
        pass

    def is_open(self) -> bool:
        return self.ble_proxy().is_connected(self.device)

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

    def is_ready(self) -> bool:
        return self._ble is not None


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
        self.process = Process(
            target=BleAsync, args=(child_pipe, log._STDERR_VERBOSITY), daemon=True
        )
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
    last_adv: float = 0.0
    client: BleakClient | None = None
    queue: asyncio.Queue | None = None

    @property
    def address(self) -> str:
        return self.device.address

    def update_timestamp(self) -> None:
        self.last_adv = time.monotonic()

    def last_seen(self) -> float:
        return time.monotonic() - self.last_adv


class BleAsync:
    class Shutdown(Exception):
        pass

    def __init__(self, pipe: Connection, log_verbosity: int | None) -> None:
        # Logging disabled in the new process, try re-setup if stderr.
        if log_verbosity is not None:
            log.enable_debug_output(log_verbosity)
        asyncio.run(self.main(pipe))

    async def main(self, pipe: Connection) -> None:
        self.devices: dict[str, Peripheral] = {}
        self.did_scan = False

        self.scanner_task: asyncio.Task | None = None
        # Notify scanner task to extend the timeout. If None, scan is either not running or shutting down and not accepting new notification.
        self.scan_timeout_reset: asyncio.Event | None = None
        # Used by scanner task to notify when self.devices changes.
        self.scan_event = asyncio.Event()
        LOG.debug("async BLE process started")

        try:
            await self._main_loop(pipe)
        finally:
            await self._stop_scan()
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

    # Keeps scan running for some time - for reliably connecting on Linux scan needs to be running
    # at the same time, however the following patter does not work reliably wrt timeouts:
    # (scan on), enumerate, (scan off), ..., (scan on), connect, (scan off)
    # So we instead end up doing:
    # (scan on), enumerate, ..., connect, ..., (scan off)
    # TODO: refactor into separate class
    async def _start_scan(self) -> None:
        if self.scan_timeout_reset is not None:
            self.scan_timeout_reset.set()
            return

        # Filter by UUID, update self.devices, notify self.scan_event.
        async def detection_callback(
            device: BLEDevice, adv_data: AdvertisementData
        ) -> None:
            if TREZOR_SERVICE_UUID not in adv_data.service_uuids:
                return

            periph = self.devices.setdefault(
                device.address, Peripheral(device, adv_data)
            )
            periph.device = device
            periph.adv_data = adv_data

            if periph.last_seen() > 0.6:
                md = ", ".join(
                    f"{hex(k)}: {v.hex()}"
                    for k, v in adv_data.manufacturer_data.items()
                )
                LOG.debug(
                    f"scan: {device.address}: {device.name} rssi={adv_data.rssi} manufacturer_data=<{md}>"
                )
            periph.update_timestamp()
            self.scan_event.set()

        # Run scan until timeout or cancel. Timeout can be extended using self.scan_timeout_reset.
        async def _scan_task() -> None:
            assert self.scan_timeout_reset is None
            self.scan_timeout_reset = asyncio.Event()

            # NOTE: filtering by UUIDs may not work on some systems/environments:
            #       https://github.com/trezor/trezor-suite/pull/21093
            # NOTE: filtering by UUIDs makes bluez-5.87 crash
            async with BleakScanner(
                detection_callback=detection_callback,
                # service_uuids=[TREZOR_SERVICE_UUID],
                # bluez={"filters": {"DuplicateData": True}},
            ):
                LOG.info("BLE discovery enabled")
                try:
                    while True:
                        await asyncio.wait_for(
                            self.scan_timeout_reset.wait(), SCAN_LINGER_SECONDS
                        )
                        self.scan_timeout_reset.clear()
                        # Reset timeout
                except TimeoutError:
                    LOG.debug("BLE discovery timed out")
                except asyncio.CancelledError:
                    LOG.debug("BLE discovery cancelled")
                finally:
                    self.scan_timeout_reset = None

            LOG.info("BLE discovery disabled")
            self.scanner_task = None

        self.scanner_task = asyncio.create_task(_scan_task())

    async def _stop_scan(self) -> None:
        if self.scanner_task is None or self.scanner_task.done():
            self.scanner_task = None
            return

        self.scanner_task.cancel()
        try:
            await self.scanner_task
        except asyncio.CancelledError:
            pass
        finally:
            self.scanner_task = None

    # throws exception when no adapters found
    async def scan(self) -> list[tuple[str, str]]:
        LOG.debug("scanning BLE")

        await self._start_scan()
        await asyncio.sleep(SCAN_INTERVAL_SECONDS)

        res = [
            (periph.address, periph.device.name)
            for periph in self.devices.values()
            if periph.device.name is not None
            and periph.last_seen() <= SCAN_INTERVAL_SECONDS
        ]
        LOG.debug(f"scan: {len(res)} devices")
        # TODO: stop scan immediatelly if 0 devices found?
        return res

    async def connect(self, address: str) -> None:
        if address in self.devices and self.devices[address].client:
            LOG.warning(f"Already connected to {address}")
            return

        # For some reason discovery must be running when connecting
        # https://github.com/bluez/bluez/issues/2503
        LOG.debug(f"Waiting for {address}")
        await self._start_scan()

        async def wait_for_address() -> Peripheral:
            while True:
                periph = self.devices.get(address)
                if periph is not None:
                    # TODO: maybe check last_seen() <= SCAN_INTERVAL_SECONDS?
                    return periph
                await self.scan_event.wait()
                self.scan_event.clear()

        try:
            periph = await asyncio.wait_for(wait_for_address(), SCAN_INTERVAL_SECONDS)
        except TimeoutError:
            raise RuntimeError(f"Device not found: {address}")

        async def disconnect_callback(client: BleakClient) -> None:
            LOG.error(f"Got disconnected from {address}")
            self.devices[address].client = None
            self.devices[address].queue = None

        LOG.debug(f"Connecting to {address}...")
        client = BleakClient(
            self.devices[address].device,
            # services=[TREZOR_SERVICE_UUID],
            timeout=CONNECT_TIMEOUT_SECONDS,
            disconnect_callback=disconnect_callback,
            # pair=(sys.platform != "darwin"),
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
                raise

        queue = asyncio.Queue()

        async def read_callback(
            characteristic: BleakGATTCharacteristic, data: bytearray
        ) -> None:
            await queue.put(data)

        await client.start_notify(
            TREZOR_CHARACTERISTIC_TX,
            read_callback,
            bluez={"use_start_notify": False},  # request exclusive access on Linux
        )
        periph.client = client
        periph.queue = queue
        LOG.info(f"Connected to {client.address}")

    async def is_connected(self, address: str) -> bool:
        return address in self.devices and self.devices[address].client is not None

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
        if periph.queue is None:
            raise RuntimeError("Connect to peripheral before reading")
        try:
            return await asyncio.wait_for(periph.queue.get(), timeout=timeout)
        except (TimeoutError, asyncio.TimeoutError) as err:
            raise Timeout(f"Timeout reading BLE packet ({timeout}s)") from err

    async def write(self, address: str, chunk: bytes) -> None:
        periph = self.devices[address]
        if periph.client is None:
            raise RuntimeError("Connect to peripheral before writing")
        await periph.client.write_gatt_char(
            TREZOR_CHARACTERISTIC_RX, chunk, response=SHOULD_WRITE_WITH_RESPONSE
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
