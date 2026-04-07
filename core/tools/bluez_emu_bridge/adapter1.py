# flake8: noqa: F722, F821

import asyncio
import logging
import random

from dbus_fast.constants import PropertyAccess
from dbus_fast.service import ServiceInterface, dbus_property, method

LOG = logging.getLogger(__name__)


class Adapter1(ServiceInterface):
    def __init__(self, bus, path, address="21:00:00:00:13:37"):
        self.bus = bus
        self.path = f"/org/bluez/{path}"
        super().__init__("org.bluez.Adapter1")
        self.address = address

        self._discovering = False
        self._devices = []

    def export(self):
        self.bus.export(self.path, self)

    def add_device(self, device):
        self._devices.append(device)

    @method()
    def SetDiscoveryFilter(self, properties: "a{sv}"):
        return

    @method()
    async def StartDiscovery(self):
        LOG.debug("dbus: StartDiscovery")
        await self._update_discovering(True)
        for device in self._devices:
            await device.task_scanning_start()
        return

    @method()
    async def StopDiscovery(self):
        LOG.debug("dbus: StopDiscovery")
        await self._update_discovering(False)
        for device in self._devices:
            device.task_scanning_stop()
        return

    @dbus_property(access=PropertyAccess.READ)
    def Address(self) -> "s":
        return self.address

    @dbus_property(access=PropertyAccess.READ)
    def AddressType(self) -> "s":
        return "public"

    @dbus_property(access=PropertyAccess.READ)
    def Alias(self) -> "s":
        return "fake-ble-adapter-4real"

    @dbus_property(access=PropertyAccess.READ)
    def Class(self) -> "u":
        return 8126732

    @dbus_property(access=PropertyAccess.READ)
    def Discoverable(self) -> "b":
        return True

    @dbus_property(access=PropertyAccess.READ)
    def DiscoverableTimeout(self) -> "u":
        return 180

    @dbus_property(access=PropertyAccess.READ)
    def Discovering(self) -> "b":
        return self._discovering

    @dbus_property(access=PropertyAccess.READ)
    def Modalias(self) -> "s":
        return "usb:v1D6Bp0246d054F"

    @dbus_property(access=PropertyAccess.READ)
    def Name(self) -> "s":
        return "fake-ble-adapter"

    @dbus_property(access=PropertyAccess.READ)
    def Pairable(self) -> "b":
        return True

    @dbus_property(access=PropertyAccess.READ)
    def PairableTimeout(self) -> "u":
        return 0

    @dbus_property(access=PropertyAccess.READWRITE)
    def Powered(self) -> "b":
        return True

    @Powered.setter
    def Powered(self, value: "b"):
        LOG.debug(f"Trying to set Powered to {value}")

    @dbus_property(access=PropertyAccess.READ)
    def Roles(self) -> "as":
        return ["central", "peripheral"]

    @dbus_property(access=PropertyAccess.READ)
    def UUIDs(self) -> "as":
        return []

    async def _update_discovering(self, new_value: bool):
        await asyncio.sleep(random.uniform(0.5, 1.5))
        self._discovering = new_value
        self.emit_properties_changed({"Discovering": self._discovering})
        LOG.debug(f"Discovering changed: {self._discovering}")
