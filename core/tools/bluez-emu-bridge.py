#!/usr/bin/env python3

import asyncio
import atexit
import logging
import subprocess
from pathlib import Path

import click
from bluez_emu_bridge import MessageBus  # normally lives in dbus_next.aio
from bluez_emu_bridge import Adapter1, Device1, GattCharacteristic1, GattService1

from trezorlib.transport.emu_ble import Command, Event

HERE = Path(__file__).parent.resolve()

SERVICE_UUID = "8c000001-a59b-4d58-a9ad-073df69fa1b1"
CHARACTERISTIC_RX = "8c000002-a59b-4d58-a9ad-073df69fa1b1"
CHARACTERISTIC_TX = "8c000003-a59b-4d58-a9ad-073df69fa1b1"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler()],
)
LOG = logging.getLogger(__name__)


class TrezorUDP(asyncio.DatagramProtocol):
    @classmethod
    async def create(cls, ip, port):
        loop = asyncio.get_running_loop()
        addr = (ip, port)
        return await loop.create_datagram_endpoint(
            lambda: TrezorUDP(addr),
            remote_addr=addr,
        )

    def __init__(self, addr):
        self.addr = addr
        self.transport = None
        self.queue = asyncio.Queue()

    def ipport(self):
        return f"{self.addr[0]}:{self.addr[1]}"

    def connection_made(self, transport: asyncio.DatagramTransport):
        self.transport = transport

    def connection_lost(self, exc: Exception | None):
        # Does this ever happen?
        LOG.error(f"{self.ipport()} Connection lost", exc_info=exc)

    def datagram_received(self, data, addr):
        if addr != self.addr:
            LOG.error(f"{self.ipport()} Stray datagram from {addr}?")
            return
        LOG.debug(f"{self.ipport()} Received len={len(data)}")
        self.queue.put_nowait(data)

    def error_received(self, exc: Exception | None):
        LOG.error(f"{self.ipport()} UDP error", exc_info=exc)

    def write(self, value: bytes):
        assert self.transport
        LOG.debug(f"{self.ipport()} Sending len={len(value)}")
        self.transport.sendto(value)

    def close(self):
        if self.transport:
            self.transport.close()
        self.queue.shutdown()


class TrezorEmulator:
    def __init__(self, data_transport, data_protocol, event_transport, event_protocol):
        self._data_transport = data_transport
        self.data_protocol = data_protocol
        self._event_transport = event_transport
        self.event_protocol = event_protocol

    def close(self):
        self.data_transport.close()
        self.event_transport.close()

    async def print_commands(self):
        while True:
            data = await self.event_protocol.queue.get()
            command = Command.parse(data)
            LOG.info(f"Emulator command: {command}")

    @classmethod
    async def create(cls, emulator_port, device, char_tx, char_rx):
        localhost = "127.0.0.1"
        data_transport, data_protocol = await TrezorUDP.create(localhost, emulator_port)

        char_rx.send_value = data_protocol.write
        data_read_task = asyncio.create_task(
            char_tx.update_from_queue(data_protocol.queue)
        )

        remote_addr = ("127.0.0.1", emulator_port + 1)
        event_transport, event_protocol = await TrezorUDP.create(
            localhost, emulator_port + 1
        )

        obj = cls(data_transport, data_protocol, event_transport, event_protocol)

        event_read_task = asyncio.create_task(device.connection_state_task(event_protocol.write, event_protocol.queue))
        # obj.event_protocol.write(Event.ping().build())

        return obj


async def emulator_main(bus_address: str, emulator_port: int):
    bus = await MessageBus(bus_address=bus_address).connect()

    hci0 = Adapter1(bus, "hci0")
    device = Device1(bus, hci0.path, "01:02:03:04:05:06")
    service = GattService1(bus, device.path, 0, SERVICE_UUID)
    char_tx = GattCharacteristic1(
        bus, service.path, 0, CHARACTERISTIC_TX, flags=["read", "notify"]
    )
    char_rx = GattCharacteristic1(
        bus,
        service.path,
        1,
        CHARACTERISTIC_RX,
        flags=["write", "write-without-response"],
    )

    service.add_characteristic(char_tx)
    service.add_characteristic(char_rx)
    device.add_service(service)
    hci0.add_device(device)
    hci0.export()

    ### might make it possible to drop the message_bus.py hack
    # from dbus_next.service import ServiceInterface
    # bus.export("/", ServiceInterface("io.trezor.Empty"))

    emulator = await TrezorEmulator.create(emulator_port, device, char_tx, char_rx)

    await bus.request_name("org.bluez")
    await bus.wait_for_disconnect()


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

    def callback():
        daemon.terminate()
        daemon.kill()

    atexit.register(callback)
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
def cli(verbose: bool, emulator_port: int, bus_address: str | None):
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    if not bus_address:
        bus_address = start_bus()
        click.echo(f"DBUS_SYSTEM_BUS_ADDRESS={bus_address}")
    # asyncio.get_event_loop().run_until_complete(emulator_main(bus_address, emulator_port))
    asyncio.run(emulator_main(bus_address, emulator_port))


if __name__ == "__main__":
    cli()
