import asyncio
import logging
import random

from dbus_next.service import PropertyAccess, ServiceInterface, dbus_property, method

LOG = logging.getLogger(__name__)


class Adapter1(ServiceInterface):
    def __init__(self, bus, path, address="00:00:00:12:34:56"):
        self.bus = bus
        self.path = path
        super().__init__("org.bluez.Adapter1")
        self._discovering = False
        self._address = address

        self._devices = []

    def export(self):
        self.bus.export(f"/org/bluez/{self.path}", self)

    def add_device(self, device):
        self._devices.append(device)

    @method()
    def SetDiscoveryFilter(self, properties: "a{sv}"):
        return

    @method()
    async def StartDiscovery(self):
        LOG.debug("StartDiscovery")
        await self._update_discoverying(True)
        for device in self._devices:
            await device.task_scanning_start()
        return

    @method()
    async def StopDiscovery(self):
        LOG.debug("StopDiscovery")
        await self._update_discoverying(False)
        for device in self._devices:
            device.task_scanning_stop()
        return

    @dbus_property(access=PropertyAccess.READ)
    def Discovering(self) -> "b":
        return self._discovering

    @dbus_property(access=PropertyAccess.READ)
    def Address(self) -> "s":
        return self._address

    @dbus_property(access=PropertyAccess.READ)
    def AddressType(self) -> "s":
        return "public"

    @dbus_property(access=PropertyAccess.READ)
    def Modalias(self) -> "s":
        return "usb:v1D6Bp0246d054F"

    @dbus_property(access=PropertyAccess.READ)
    def Name(self) -> "s":
        return "fake-ble-adapter"

    @dbus_property(access=PropertyAccess.READ)
    def Alias(self) -> "s":
        return "fake-ble-adapter-4real"

    @dbus_property(access=PropertyAccess.READWRITE)
    def Powered(self) -> "b":
        return True

    @Powered.setter
    def Powered(self, value: "b"):
        LOG.debug(f"Trying to set Powered to {value}")

    async def _update_discoverying(self, new_value: bool):
        await asyncio.sleep(random.uniform(0.5, 1.5))
        self._discovering = new_value
        self.emit_properties_changed({"Discovering": self._discovering})
        LOG.debug(f"Discovering changed: {self._discovering}")
