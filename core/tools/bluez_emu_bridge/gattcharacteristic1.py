import asyncio
import logging
import random

from dbus_next.service import PropertyAccess, ServiceInterface, dbus_property, method

LOG = logging.getLogger(__name__)


class GattCharacteristic1(ServiceInterface):
    def __init__(self, bus, parent_path, id_num, uuid, flags=None):
        self.bus = bus
        self.path = f"{parent_path}/char{id_num:04x}"
        super().__init__("org.bluez.GattCharacteristic1")
        self._service = f"/org/bluez/{parent_path}"
        self._uuid = uuid
        self._value = bytes()
        self._flags = flags if flags is not None else []
        self._notifying = False
        self._exported = False
        self.send_value = None

    def export(self):
        if not self._exported:
            self.bus.export(f"/org/bluez/{self.path}", self)
            self._exported = True

    def update_value(self, new_value: bytes):
        self._update_value(new_value)

    @method()
    async def StartNotify(self):
        LOG.debug(f"{self.path}: StartNotify")
        await self._update_notifying(True)

    @method()
    async def StopNotify(self):
        LOG.debug(f"{self.path}: StartNotify")
        await self._update_notifying(False)

    @method()
    def ReadValue(self, options: "a{sv}") -> "ay":
        LOG.debug(f"{self.path}: ReadValue (len={len(self._value)})")
        return self._value

    @method()
    def WriteValue(self, value: "ay", options: "a{sv}"):
        LOG.debug(f"{self.path}: WriteValue (len={len(value)})")
        if not self.send_value:
            self._update_value(value)
        else:
            self.send_value(value)

    # TODO: AcquireWrite, AcquireNotify for trezorlib+tealblue

    @dbus_property(access=PropertyAccess.READ)
    def Notifying(self) -> "b":
        return self._notifying

    @dbus_property(access=PropertyAccess.READ)
    def UUID(self) -> "s":
        return self._uuid

    @dbus_property(access=PropertyAccess.READ)
    def Value(self) -> "ay":
        return self._value

    @dbus_property(access=PropertyAccess.READ)
    def Flags(self) -> "as":
        return self._flags

    @dbus_property(access=PropertyAccess.READ)
    def Service(self) -> "s":
        return self._service

    def _update_value(self, new_value: bytes):
        self._value = new_value
        if self._notifying:
            property_changed = {"Value": self._value}
            self.emit_properties_changed(property_changed)

    async def _update_notifying(self, new_value: bool):
        # await asyncio.sleep(random.uniform(0.0, 0.2))
        self._notifying = new_value
        property_changed = {"Notifying": self._notifying}
        self.emit_properties_changed(property_changed)

    async def update_from_queue(self, queue):
        while True:
            val = await queue.get()
            if not self._notifying:
                LOG.warning("Got message from emulator while Notifying=false")
            self.update_value(val)
