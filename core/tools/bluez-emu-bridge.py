#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false, reportGeneralTypeIssues=false, reportReturnType=false
"""
The purpose of this script is to create a mock D-Bus API of BlueZ, the Linux Bluetooth protocol
stack. Using environment variables you can trick programs to use this API instead of the system
one to talk to Trezor emulator as if it was a BLE device.

BlueZ API docs: https://github.com/bluez/bluez/tree/master/doc
D-Bus: https://www.freedesktop.org/wiki/Software/dbus/
Debugger: https://apps.gnome.org/en-GB/Dspy/
Sniffer: https://dbus.freedesktop.org/doc/dbus-monitor.1.html
Based on: https://github.com/simpleble/python_bluez_dbus_emulator
"""

import asyncio
import atexit
import logging
import subprocess
from pathlib import Path

import click
from bluez_emu_bridge import MessageBus  # normally lives in dbus_fast.aio
from bluez_emu_bridge import Adapter1, Device1, GattCharacteristic1, GattService1
from typing_extensions import Self

from trezorlib._internal.emu_ble import Event
from trezorlib.transport.ble import (
    TREZOR_CHARACTERISTIC_RX,
    TREZOR_CHARACTERISTIC_TX,
    TREZOR_SERVICE_UUID,
)

HERE = Path(__file__).parent.resolve()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[logging.StreamHandler()],
)
LOG = logging.getLogger(__name__)


class TrezorUDP(asyncio.DatagramProtocol):
    @classmethod
    async def create(cls, ip: str, port: int) -> Self:
        loop = asyncio.get_running_loop()
        addr = (ip, port)
        return await loop.create_datagram_endpoint(
            lambda: TrezorUDP(addr),
            remote_addr=addr,
        )

    def __init__(self, addr: tuple[str, int]) -> None:
        self.addr = addr
        self.transport = None
        self.queue = asyncio.Queue()

    def ipport(self) -> str:
        return f"{self.addr[0]}:{self.addr[1]}"

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        self.transport = transport

    def connection_lost(self, exc: Exception | None) -> None:
        # Does this ever happen?
        LOG.error(f"{self.ipport()} Connection lost", exc_info=exc)

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        if addr != self.addr:
            LOG.error(f"{self.ipport()} Stray datagram from {addr}?")
            return
        self.queue.put_nowait(data)

    def error_received(self, exc: Exception | None) -> None:
        LOG.error(f"{self.ipport()} UDP error", exc_info=exc)

    def write(self, value: bytes) -> None:
        assert self.transport
        self.transport.sendto(value)

    def close(self) -> None:
        if self.transport:
            self.transport.close()
            self.transport = None
        self.queue.shutdown()


class TrezorEmulator:

    def __init__(
        self,
        data_transport: asyncio.DatagramTransport,
        data_protocol: TrezorUDP,
        data_read_task: asyncio.Task,
        event_transport: asyncio.DatagramTransport,
        event_protocol: TrezorUDP,
        event_read_task: asyncio.Task,
    ) -> None:
        self._data_transport = data_transport
        self.data_protocol = data_protocol
        self.data_read_task = data_read_task
        self._event_transport = event_transport
        self.event_protocol = event_protocol
        self.event_read_task = event_read_task

    def close(self) -> None:
        self.data_transport.close()
        self.event_transport.close()

    @classmethod
    async def create(
        cls,
        emulator_port: int,
        device: Device1,
        char_tx: GattCharacteristic1,
        char_rx: GattCharacteristic1,
    ) -> Self:
        localhost = "127.0.0.1"
        data_transport, data_protocol = await TrezorUDP.create(localhost, emulator_port)

        char_rx.send_value = data_protocol.write
        data_read_task = asyncio.create_task(
            char_tx.update_from_queue(data_protocol.queue)
        )

        event_transport, event_protocol = await TrezorUDP.create(
            localhost, emulator_port + 1
        )
        event_read_task = asyncio.create_task(
            device.connection_state_task(event_protocol.write, event_protocol.queue)
        )
        obj = cls(
            data_transport,
            data_protocol,
            data_read_task,
            event_transport,
            event_protocol,
            event_read_task,
        )
        # Ping the emulator so that it knows our UDP port and sends us the current state.
        # NOTE: Assumes emulator is running, othewise a loop is needed.
        obj.event_protocol.write(Event.ping().build())

        return obj


async def emulator_main(bus_address: str, emulator_port: int) -> None:
    bus = await MessageBus(bus_address=bus_address).connect()

    hci0 = Adapter1(bus, "hci0")
    device = Device1(bus, hci0)
    service = GattService1(bus, device.path, 0, TREZOR_SERVICE_UUID)
    char_tx = GattCharacteristic1(
        bus, service.path, 0, TREZOR_CHARACTERISTIC_TX, flags=["read", "notify"]
    )
    char_rx = GattCharacteristic1(
        bus,
        service.path,
        1,
        TREZOR_CHARACTERISTIC_RX,
        flags=["write", "write-without-response"],
    )

    service.add_characteristic(char_tx)
    service.add_characteristic(char_rx)
    device.add_service(service)
    hci0.add_device(device)
    hci0.export()

    emulator = await TrezorEmulator.create(emulator_port, device, char_tx, char_rx)

    await bus.request_name("org.bluez")
    await bus.wait_for_disconnect()
    emulator.close()
    LOG.info("End emulator_main")


def start_bus() -> str:
    daemon = subprocess.Popen(
        (
            "dbus-daemon",
            "--print-address",
            "--config-file",
            HERE / "bluez_emu_bridge" / "dbus-daemon.conf",
        ),
        stdout=subprocess.PIPE,
        encoding="utf-8",
    )

    def callback() -> None:
        daemon.terminate()
        daemon.kill()

    atexit.register(callback)
    assert daemon.stdout is not None
    address = daemon.stdout.readline().strip()
    LOG.info(f"dbus-daemon listening at {address}")
    parts = address.split(",")
    parts = filter(lambda p: not p.startswith("guid="), parts)
    address = ",".join(parts)
    return address


@click.command()
@click.option(
    "--bus-address",
    help="Connect to D-Bus address. If not provided, private D-Bus instance will be launched.",
)
@click.option("-v", "--verbose", is_flag=True, help="Show additional info.")
@click.option(
    "-p",
    "--emulator-port",
    type=int,
    default=21328,
    help="Trezor emulated BLE port to connect to.",
)
def cli(verbose: bool, emulator_port: int, bus_address: str | None) -> None:
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    if not bus_address:
        bus_address = start_bus()
        click.echo(f"DBUS_SYSTEM_BUS_ADDRESS={bus_address}")
    asyncio.run(emulator_main(bus_address, emulator_port))


if __name__ == "__main__":
    cli()
