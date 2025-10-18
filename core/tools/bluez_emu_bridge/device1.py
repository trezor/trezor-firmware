# flake8: noqa: F722, F821

import asyncio
import logging
import random

from dbus_fast import DBusError, Variant
from dbus_fast.constants import PropertyAccess
from dbus_fast.service import ServiceInterface, dbus_property, method

from trezorlib._internal.emu_ble import Command, CommandType, Event, EventType, ModeType

LOG = logging.getLogger(__name__)
PAIRING_TIMEOUT_SEC = 10


def mac2bytes(mac_str):
    return bytes.fromhex(mac_str.replace(":", ""))


def bytes2mac(mac_bytes):
    ":".join(map(hex, mac_bytes))


class Device1(ServiceInterface):
    def __init__(self, bus, adapter, mac_address="e1:e2:e3:e4:e5:e6"):
        self.bus = bus
        self.adapter = adapter.path
        self.adapter_mac = adapter.address
        self.path = f"{self.adapter}/dev_{'_'.join(mac_address.split(':'))}"
        super().__init__("org.bluez.Device1")
        self._exported = False

        # controlled by emulator
        self._mode = None
        self._connected = False
        self._bonds = []
        self._name = "Not set yet"

        self._pairing_result = asyncio.Queue(1)  # XXX always replace?
        self._services_resolved = False
        self._rssi = -66
        self._address = mac_address
        self._services = []

        self.send_event_fn = None
        self.command_queue = None

        self.__task_scanning_active = False

    def is_bonded(self):
        return self.adapter_mac in self._bonds

    def is_pairing(self):
        return self._mode == ModeType.PAIRING

    def is_visible(self):
        is_connectable = self._mode == ModeType.CONNECTABLE
        return self.is_pairing() or (is_connectable and self.is_bonded())

    async def export(self):
        if not self._exported:
            self._exported = True
            await asyncio.sleep(random.uniform(0.5, 1.5))
            self.bus.export(self.path, self)

    def add_service(self, service):
        self._services.append(service)

    async def task_scanning_start(self):
        await self.export()
        self.__task_scanning_active = True
        asyncio.create_task(self._task_scanning_run())

    def task_scanning_stop(self):
        self.__task_scanning_active = False

    async def _task_scanning_run(self):
        await asyncio.sleep(random.uniform(0.02, 0.2))
        if self.is_visible():
            # We need to emit PropertyChanged signal for (at least) bleak to see the device.
            # Like random RSSI.
            await self._update_rssi(random.uniform(-90, -60))
        if self.__task_scanning_active:
            asyncio.create_task(self._task_scanning_run())

    @method()
    async def Connect(self):
        LOG.debug("dbus: Connect")
        await self.do_connect()

    async def do_connect(self):
        if not self._connected:
            self.send_event(
                Event.new(
                    event_type=EventType.CONNECTED,
                    data=mac2bytes(self.adapter_mac),
                )
            )
        await self._update_connected(True)
        for service in self._services:
            service.export()
        await self._update_services_resolved(True)

    @method()
    async def Disconnect(self):
        LOG.debug("dbus: Disconnect")
        await self.do_disconnect()

    async def do_disconnect(self):
        if self._connected:
            self.send_event(Event.new(event_type=EventType.DISCONNECTED))
        await self._update_services_resolved(False)  # not sure
        await self._update_connected(False)

    @method()
    async def Pair(self):
        LOG.debug("dbus: Pair")
        if not self._connected:
            await self.do_connect()

        if self.is_bonded():
            return

        if not self.is_pairing():
            raise DBusError("org.bluez.Device1", "not in pairing mode")

        self.send_event(Event.new(event_type=EventType.PAIRING_REQUEST, data=b"999999"))
        try:
            is_paired_now = await asyncio.wait_for(
                self._pairing_result.get(), PAIRING_TIMEOUT_SEC
            )
        except asyncio.TimeoutError:
            LOG.error("Timed out waiting for Trezor to accept")
            self.send_event(Event.new(event_type=EventType.PAIRING_CANCELLED))
            await self.do_disconnect()
            # TODO: check which error bluez actually returns
            raise DBusError("org.bluez.Device1", "Timed out waiting for peripheral")

        await self._update_paired(is_paired_now)
        if is_paired_now:
            self.send_event(Event.new(event_type=EventType.PAIRING_COMPLETED))
            # we should receive updated bonds afterwards
        else:
            await self.do_disconnect()

    @method()
    async def CancelPairing(self):
        LOG.debug("dbus: CancelPairing")
        self.send_event(Event.new(event_type=EventType.PAIRING_CANCELLED))

    @dbus_property(access=PropertyAccess.READ)
    def Adapter(self) -> "o":
        return self.adapter

    @dbus_property(access=PropertyAccess.READ)
    def Address(self) -> "s":
        return self._address

    @dbus_property(access=PropertyAccess.READ)
    def AddressType(self) -> "s":
        return "random"

    @dbus_property(access=PropertyAccess.READ)
    def AdvertisingFlags(self) -> "ay":
        return b"\x06"

    @dbus_property(access=PropertyAccess.READ)
    def Alias(self) -> "s":
        return self._name

    @dbus_property(access=PropertyAccess.READ)
    def Appearance(self) -> "q":
        return 128

    @dbus_property(access=PropertyAccess.READ)
    def Bonded(self) -> "b":
        return self.is_bonded()

    @dbus_property(access=PropertyAccess.READ)
    def Blocked(self) -> "b":
        return False

    @dbus_property(access=PropertyAccess.READ)
    def Connected(self) -> "b":
        return self._connected

    @dbus_property(access=PropertyAccess.READ)
    def Icon(self) -> "s":
        return "computer"

    @dbus_property(access=PropertyAccess.READ)
    def LegacyPairing(self) -> "b":
        return False

    @dbus_property(access=PropertyAccess.READ)
    def ManufacturerData(self) -> "a{qv}":
        # 0xf29
        return {3881: Variant("ay", b"\x01\x00\x06\x00\x00\x00")}

    @dbus_property(access=PropertyAccess.READ)
    def Modalias(self) -> "s":
        return "usb:v1D6Bp0246d054F"

    @dbus_property(access=PropertyAccess.READ)
    def Name(self) -> "s":
        return self._name

    @dbus_property(access=PropertyAccess.READ)
    def Paired(self) -> "b":
        return self.is_bonded()

    @dbus_property(access=PropertyAccess.READ)
    def RSSI(self) -> "n":
        return self._rssi

    @dbus_property(access=PropertyAccess.READ)
    def ServicesResolved(self) -> "b":
        return self._services_resolved

    @dbus_property(access=PropertyAccess.READWRITE)
    def Trusted(self) -> "b":
        return True

    @Trusted.setter
    def Trusted(self, value: "b"):
        LOG.debug(f"Trying to set Trusted to {value}")

    @dbus_property(access=PropertyAccess.READ)
    def TxPower(self) -> "n":
        return 7

    @dbus_property(access=PropertyAccess.READ)
    def UUIDs(self) -> "as":
        uuids = []
        for srv in self._services:
            uuids.append(srv._uuid)
            for chr in srv._characteristics:
                uuids.append(chr._uuid)
        return uuids

    async def _update_connected(self, new_value: bool):
        await asyncio.sleep(random.uniform(0.5, 1.5))
        property_changed = {"Connected": new_value}
        self.emit_properties_changed(property_changed)
        LOG.debug(f"Property changed: {property_changed}")

    async def _update_services_resolved(self, new_value: bool):
        await asyncio.sleep(random.uniform(0.0, 0.5))
        self._services_resolved = new_value
        property_changed = {"ServicesResolved": self._services_resolved}
        self.emit_properties_changed(property_changed)
        LOG.debug(f"Property changed: {property_changed}")

    async def _update_paired(self, new_value: bool):
        property_changed = {"Paired": new_value}
        self.emit_properties_changed(property_changed)
        LOG.debug(f"Property changed: {property_changed}")

    async def _update_rssi(self, new_value: int):
        self._rssi = int(new_value)
        property_changed = {"RSSI": self._rssi}
        self.emit_properties_changed(property_changed)

    async def connection_state_task(self, write_fn, queue):
        self.send_event_fn = write_fn
        self.command_queue = queue
        self.send_event(Event.ping())
        while True:
            command = await queue.get()
            LOG.debug(f"Emulator sent command: {command}")
            await self.handle_command(command)

    async def handle_command(self, command):
        # handle new status from mock driver
        command = Command.parse(command)

        LOG.debug(f"Command {command}")
        t = command.command_type
        if t == CommandType.STATUS:
            pass
        elif t == CommandType.PAIRING_MODE:
            pass
        elif t == CommandType.DISCONNECT:
            await self.do_disconnect()
        elif t == CommandType.ALLOW_PAIRING:
            self._pairing_result.put_nowait(True)
        elif t == CommandType.REJECT_PAIRING:
            self._pairing_result.put_nowait(False)
        else:
            LOG.error(f"Command not implemented: {command}")

        m = command.mode
        if m == ModeType.PAIRING:
            pass
            # TODO emit property changed?
        elif m == ModeType.DFU:
            LOG.error("DFU mode not implemented")

        if m != self._mode:
            LOG.debug(f"Mode {self._mode} -> {m}")
            self._mode = m

        name = command.adv_name.rstrip(b"\x00").decode()
        if name:
            self._name = name
            LOG.debug(f"Changed advertising name to {name}")
        self._bonds = [bytes2mac(b) for b in command.bonds]

        connected = command.connected
        if connected != self._connected:
            LOG.debug(f"Connected {self._connected} -> {connected}")
            self._connected = bool(connected)

    def send_event(self, event):
        if self.send_event_fn is None:
            LOG.error(f"Cannot send event {event}")
        else:
            LOG.debug(f"Sending event {event}")
            self.send_event_fn(event.build())
