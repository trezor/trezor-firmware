# !/usr/bin/python3
# pyright: off

import asyncio
import io
import logging

import dbus_next

LOG = logging.getLogger(__name__)


def unwrap_properties(properties):
    return {k: v.value for k, v in properties.items()}


class TealBlue:
    @classmethod
    async def create(cls):
        self = cls()
        self._bus = await dbus_next.aio.MessageBus(
            bus_type=dbus_next.constants.BusType.SYSTEM, negotiate_unix_fd=True
        ).connect()
        obj = await self.get_object("org.bluez", "/")
        self._bluez = obj.get_interface("org.freedesktop.DBus.ObjectManager")

        return self

    async def find_adapter(self, mac_filter=""):
        """Find the first adapter matching mac_filter."""
        objects = await self._bluez.call_get_managed_objects()
        for path in sorted(objects.keys()):
            interfaces = objects[path]
            if "org.bluez.Adapter1" not in interfaces:
                continue
            properties = unwrap_properties(interfaces["org.bluez.Adapter1"])
            if mac_filter not in properties["Address"]:
                continue
            return await Adapter.create(self, path, properties)
        raise Exception("No adapter found")

    async def get_object(self, name, path):
        introspection = await self._bus.introspect(name, path)
        obj = self._bus.get_proxy_object(name, path, introspection)
        return obj


class Adapter:
    @classmethod
    async def create(cls, teal, path, properties):
        self = cls()
        self._teal = teal
        self._path = path
        self._properties = properties
        obj = await self._teal.get_object("org.bluez", path)
        self._object = obj.get_interface("org.bluez.Adapter1")

        return self

    def __repr__(self):
        return "<tealblue.Adapter address=%s>" % (self._properties["Address"])

    async def devices(self):
        """
        Returns the devices that BlueZ has discovered.
        """
        objects = await self._teal._bluez.call_get_managed_objects()
        devices = []
        for path in sorted(objects.keys()):
            interfaces = objects[path]
            if "org.bluez.Device1" not in interfaces:
                continue
            properties = unwrap_properties(interfaces["org.bluez.Device1"])
            devices.append(await Device.create(self._teal, path, properties))

        return devices

    async def scan(self, timeout_s):
        return await Scanner.create(self._teal, self, await self.devices(), timeout_s)


class Scanner:
    @classmethod
    async def create(cls, teal, adapter, initial_devices, timeout_s):
        self = cls()
        self._teal = teal
        self._adapter = adapter
        self._was_discovering = adapter._properties[
            "Discovering"
        ]  # TODO get current value, or watch property changes
        self._queue = asyncio.Queue()
        self.timeout_s = timeout_s
        for device in initial_devices:
            self._queue.put_nowait((device._path, device._properties))

        self._teal._bluez.on_interfaces_added(self._on_iface_added)
        if not self._was_discovering:
            await self._adapter._object.call_start_discovery()

        return self

    def _on_iface_added(self, path, interfaces):
        if "org.bluez.Device1" not in interfaces:
            return
        if not path.startswith(self._adapter._path + "/"):
            return
        properties = unwrap_properties(interfaces["org.bluez.Device1"])
        self._queue.put_nowait((path, properties))

    async def __aenter__(self):
        return self

    async def __aexit__(self, type, value, traceback):
        if not self._was_discovering:
            await self._adapter._object.call_stop_discovery()
        self._teal._bluez.off_interfaces_added(self._on_iface_added)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            (path, properties) = await asyncio.wait_for(
                self._queue.get(), self.timeout_s
            )
            return await Device.create(self._teal, path, properties)
        except asyncio.TimeoutError:
            raise StopAsyncIteration


class Device:
    @classmethod
    async def create(cls, teal, path, properties):
        self = cls()
        self._teal = teal
        self._path = path
        self._properties = properties
        self._services_resolved = asyncio.Event()
        self._services = None

        if properties["ServicesResolved"]:
            self._services_resolved.set()

        # Listen to device events (connect, disconnect, ServicesResolved, ...)
        obj = await self._teal.get_object("org.bluez", path)
        self._device = obj.get_interface("org.bluez.Device1")
        obj = await self._teal.get_object("org.bluez", path)
        self._device_props = obj.get_interface("org.freedesktop.DBus.Properties")
        self._device_props.on_properties_changed(self._on_prop_changed)

        return self

    def __del__(self):
        self._device_props.off_properties_changed(self._on_prop_changed)

    def __repr__(self):
        return "<tealblue.Device address=%s name=%r>" % (self.address, self.name)

    def _on_prop_changed(self, _interface, changed_props, invalidated_props):
        changed_props = unwrap_properties(changed_props)
        LOG.debug(
            f"prop changed: device {self._path} {changed_props.keys()} {invalidated_props}"
        )
        for key, value in changed_props.items():
            self._properties[key] = value
        for key in invalidated_props:
            del self._properties[key]

        if "ServicesResolved" in changed_props:
            if changed_props["ServicesResolved"]:
                self._services_resolved.set()
            else:
                self._services_resolved.clear()

    async def connect(self):
        await self._device.call_connect()

    async def disconnect(self):
        await self._device.call_disconnect()

    async def services(self):
        await self._services_resolved.wait()
        if self._services is None:
            self._services = {}
            objects = await self._teal._bluez.call_get_managed_objects()
            for path in sorted(objects.keys()):
                if not path.startswith(self._path + "/"):
                    continue
                if "org.bluez.GattService1" in objects[path]:
                    properties = unwrap_properties(
                        objects[path]["org.bluez.GattService1"]
                    )
                    service = Service(self._teal, self, path, properties)
                    self._services[service.uuid] = service
                elif "org.bluez.GattCharacteristic1" in objects[path]:
                    properties = unwrap_properties(
                        objects[path]["org.bluez.GattCharacteristic1"]
                    )
                    characterstic = await Characteristic.create(
                        self._teal, self, path, properties
                    )
                    for service in self._services.values():
                        if properties["Service"] == service._path:
                            service.characteristics[characterstic.uuid] = characterstic
        return self._services

    @property
    def connected(self):
        return bool(self._properties["Connected"])

    @property
    def services_resolved(self):
        return bool(self._properties["ServicesResolved"])

    @property
    def UUIDs(self):
        return [str(s) for s in self._properties["UUIDs"]]

    @property
    def address(self):
        return str(self._properties["Address"])

    @property
    def name(self):
        if "Name" not in self._properties:
            return None
        return str(self._properties["Name"])

    @property
    def alias(self):
        if "Alias" not in self._properties:
            return None
        return str(self._properties["Alias"])


class Service:
    def __init__(self, teal, device, path, properties):
        self._device = device
        self._teal = teal
        self._path = path
        self._properties = properties
        self.characteristics = {}

    def __repr__(self):
        return "<tealblue.Service device=%s uuid=%s>" % (
            self._device.address,
            self.uuid,
        )

    @property
    def uuid(self):
        return str(self._properties["UUID"])


class Characteristic:
    def __init__(self):
        self._properties = {}

    @classmethod
    async def create(cls, teal, device, path, properties):
        self = cls()
        self._device = device
        self._teal = teal
        self._path = path
        self._properties = properties
        self._values = asyncio.Queue()

        obj = await self._teal.get_object("org.bluez", path)
        self._char = obj.get_interface("org.bluez.GattCharacteristic1")
        self._props = obj.get_interface("org.freedesktop.DBus.Properties")
        self._props.on_properties_changed(self._on_prop_changed)

        return self

    def __repr__(self):
        return "<tealblue.Characteristic device=%s uuid=%s>" % (
            self._device.address,
            self.uuid,
        )

    def __del__(self):
        self._props.off_properties_changed(self._on_prop_changed)

    def _on_prop_changed(self, _interface, changed_props, invalidated_props):
        changed_props = unwrap_properties(changed_props)
        LOG.debug(
            f"prop changed: characteristic {changed_props.keys()} {invalidated_props}"
        )
        for key, value in changed_props.items():
            self._properties[key] = bytes(value)
        for key in invalidated_props:
            del self._properties[key]

        if "Value" in changed_props:
            self._values.put_nowait(changed_props["Value"])

    async def acquire(self, write: bool = False) -> tuple[io.FileIO, int]:
        if write:
            fd, mtu = await self._char.call_acquire_write({})
            mode = "w"
        else:
            fd, mtu = await self._char.call_acquire_notify({})
            mode = "r"

        f = io.FileIO(fd, mode)
        LOG.debug(f"acquired {self.uuid} ({mode})")
        return f, mtu

    async def read(self) -> bytes:
        return bytes(await self._values.get())

    async def write(self, value, command=True):
        ty = "command" if command else "request"
        await self._char.call_write_value(value, {"type": dbus_next.Variant("s", ty)})

    #
    #    async def write(self, value, command=True):
    #        start = time.time()
    #        try:
    #            if command:
    #                await self._char.call_write_value(value, {"type": "command"})
    #            else:
    #                await self._char.call_write_value(value, {"type": "request"})
    #
    #        except dbus_next.DBusError as e:
    #            if (
    #                e.type == "org.bluez.Error.Failed"
    #                and e.text == "Not connected"
    #            ):
    #                raise NotConnectedError()
    #            else:
    #                raise  # some other error
    #
    #        # Workaround: if the write took very long, it is possible the connection
    #        # broke (without causing an exception). So check whether we are still
    #        # connected.
    #        # I think this is a bug in BlueZ.
    #        if time.time() - start > 0.5:
    #            if not self._device._device_props.call_get("org.bluez.Device1", "Connected"):
    #                raise NotConnectedError()

    async def start_notify(self):
        await self._char.call_start_notify()

    async def stop_notify(self):
        await self._char.call_stop_notify()

    @property
    def uuid(self):
        return str(self._properties["UUID"])
