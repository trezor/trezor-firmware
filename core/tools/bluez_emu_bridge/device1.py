import asyncio
import logging
import random

from dbus_next import Variant
from dbus_next.service import PropertyAccess, ServiceInterface, dbus_property, method

from trezorlib.transport.emu_ble import Command, CommandType, Event, EventType

LOG = logging.getLogger(__name__)


class Device1(ServiceInterface):
    def __init__(self, bus, parent_path, mac_address="00:00:00:00:00:00"):
        self.bus = bus
        self.path = f"{parent_path}/dev_{'_'.join(mac_address.split(':'))}"
        super().__init__("org.bluez.Device1")
        self._exported = False
        self._connected = False
        self._paired = False
        self._pairing_result = asyncio.Queue(1)
        self._services_resolved = False
        self._rssi = -66
        self._address = mac_address
        self._name = "Trezor Emulator"  # Suite looks for Trezor prefix
        self._services = []

        self.send_event_fn = None
        self.command_queue = None

        self.__task_scanning_active = False

    async def export(self):
        if not self._exported:
            self._exported = True
            await asyncio.sleep(random.uniform(0.5, 1.5))
            self.bus.export(f"/org/bluez/{self.path}", self)

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
        # Execute scanning tasks
        await self._update_rssi(random.uniform(-90, -60))
        if self.__task_scanning_active:
            asyncio.create_task(self._task_scanning_run())

    @method()
    async def Connect(self):
        LOG.debug("Connect")
        await self.do_connect()

    async def do_connect(self):
        if not self._connected:
            self.send_event(Event.new(event_type=EventType.CONNECTED))
        await self._update_connected(True)
        for service in self._services:
            service.export()
        await self._update_services_resolved(True)

    @method()
    async def Disconnect(self):
        LOG.debug("Disconnect")
        await self.do_disconnect()

    async def do_disconnect(self):
        if self._connected:
            self.send_event(Event.new(event_type=EventType.DISCONNECTED))
        await self._update_services_resolved(False)
        await self._update_connected(False)

    @method()
    async def Pair(self):
        LOG.debug("Pair")
        if not self._connected:
            await self.do_connect()

        if not self._paired:
            self.send_event(Event.new(event_type=EventType.PAIRING_REQUEST, data=b"999999"))
            is_paired_now = await self._pairing_result.get()
            await self._update_paired(is_paired_now)
            if not is_paired_now:
                await self.do_disconnect()

    @method()
    async def CancelPairing(self):
        LOG.debug("CancelPairing")
        self.send_event(Event.new(event_type=EventType.PAIRING_CANCELLED))

    @dbus_property(access=PropertyAccess.READ)
    def ManufacturerData(self) -> "a{qv}":
        return {65535: Variant("ay", b"\x01\x00\x54\x32\x57\x31")}

    @dbus_property(access=PropertyAccess.READ)
    def Connected(self) -> "b":
        return self._connected

    @dbus_property(access=PropertyAccess.READ)
    def ServicesResolved(self) -> "b":
        return self._services_resolved

    @dbus_property(access=PropertyAccess.READ)
    def RSSI(self) -> "n":
        return self._rssi

    @dbus_property(access=PropertyAccess.READ)
    def Name(self) -> "s":
        return self._name

    @dbus_property(access=PropertyAccess.READ)
    def Address(self) -> "s":
        return self._address

    @dbus_property(access=PropertyAccess.READ)
    def UUIDs(self) -> "as":
        uuids = []
        for srv in self._services:
            uuids.append(srv._uuid)
            for chr in srv._characteristics:
                uuids.append(chr._uuid)
        return uuids

    @dbus_property(access=PropertyAccess.READ)
    def AddressType(self) -> "s":
        return "random"

    @dbus_property(access=PropertyAccess.READ)
    def Paired(self) -> "b":
        return self._paired

    @dbus_property(access=PropertyAccess.READ)
    def Trusted(self) -> "b":
        return True

    @dbus_property(access=PropertyAccess.READ)
    def Blocked(self) -> "b":
        return False

    @dbus_property(access=PropertyAccess.READ)
    def LegacyPairing(self) -> "b":
        return False

    async def _update_connected(self, new_value: bool):
        await asyncio.sleep(random.uniform(0.5, 1.5))
        self._connected = new_value
        property_changed = {"Connected": self._connected}
        self.emit_properties_changed(property_changed)
        LOG.debug(f"Property changed: {property_changed}")

    async def _update_services_resolved(self, new_value: bool):
        await asyncio.sleep(random.uniform(0.0, 0.5))
        self._services_resolved = new_value
        property_changed = {"ServicesResolved": self._services_resolved}
        self.emit_properties_changed(property_changed)
        LOG.debug(f"Property changed: {property_changed}")

    async def _update_paired(self, new_value: bool):
        # TODO return if not changed?
        self._paired = new_value
        property_changed = {"Paired": self._paired}
        self.emit_properties_changed(property_changed)
        LOG.debug(f"Property changed: {property_changed}")

    async def _update_rssi(self, new_value: int):
        return  # FIXME skip
        self._rssi = int(new_value)
        property_changed = {"RSSI": self._rssi}
        self.emit_properties_changed(property_changed)

    async def connection_state_task(self, write_fn, queue):
        self.send_event_fn = write_fn
        self.command_queue = queue
        self.send_event(Event.ping())
        while True:
            command = await queue.get()
            command = Command.parse(command)
            LOG.debug(f"Emulator sent command: {command}")
            t = command.command_type
            if t == CommandType.ALLOW_PAIRING:
                self._pairing_result.put_nowait(True)
            elif t == CommandType.REJECT_PAIRING:
                self._pairing_result.put_nowait(False)
            elif t == CommandType.EMULATOR_PONG:
                LOG.info("Emulator pong")
            else:
                LOG.error(f"Command not implemented: {command}")

    def send_event(self, event):
        if self.send_event_fn is None:
            LOG.error(f"Cannot send event {event}")
        else:
            LOG.debug(f"Sending event {event}")
            self.send_event_fn(event.build())
