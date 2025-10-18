# flake8: noqa: F722, F821

from dbus_fast.constants import PropertyAccess
from dbus_fast.service import ServiceInterface, dbus_property


class GattService1(ServiceInterface):
    def __init__(self, bus, parent_path, id_num, uuid):
        self.bus = bus
        self.parent_path = parent_path
        self.path = f"{parent_path}/service{id_num:04x}"
        super().__init__("org.bluez.GattService1")
        self._uuid = uuid
        self._exported = False
        self._characteristics = []

    def export(self):
        if not self._exported:
            self.bus.export(self.path, self)
            for char in self._characteristics:
                char.export()
            self._exported = True

    def add_characteristic(self, characteristic):
        self._characteristics.append(characteristic)

    @dbus_property(access=PropertyAccess.READ)
    def Device(self) -> "o":
        return self.parent_path

    @dbus_property(access=PropertyAccess.READ)
    def UUID(self) -> "s":
        return self._uuid

    @dbus_property(access=PropertyAccess.READ)
    def Primary(self) -> "b":
        return True

    @dbus_property(access=PropertyAccess.READ)
    def Includes(self) -> "as":
        return []
