#!/usr/bin/python3

import queue
import threading
import time

import dbus
import dbus.mainloop.glib
import dbus.service


class NotConnectedError(Exception):
    pass


class DBusInvalidArgsException(dbus.exceptions.DBusException):
    _dbus_error_name = "org.freedesktop.DBus.Error.InvalidArgs"


def format_uuid(uuid):
    if type(uuid) == int:
        if uuid > 0xFFFF:
            raise ValueError("32-bit UUID not supported yet")
        uuid = "%04X" % uuid
    return uuid


class TealBlue:
    def __init__(self):
        self._bus = dbus.SystemBus()
        self._bluez = dbus.Interface(
            self._bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager"
        )

    def find_adapter(self):
        # find the first adapter
        objects = self._bluez.GetManagedObjects()
        for path in sorted(objects.keys()):
            interfaces = objects[path]
            if "org.bluez.Adapter1" not in interfaces:
                continue
            properties = interfaces["org.bluez.Adapter1"]
            return Adapter(self, path, properties)
        return None  # no adapter found

    # copied from:
    # https://github.com/adafruit/Adafruit_Python_BluefruitLE/blob/master/Adafruit_BluefruitLE/bluez_dbus/provider.py
    def _print_tree(self):
        """Print tree of all bluez objects, useful for debugging."""
        # This is based on the bluez sample code get-managed-objects.py.
        objects = self._bluez.GetManagedObjects()
        for path in sorted(objects.keys()):
            print("[ %s ]" % (path))
            interfaces = objects[path]
            for interface in sorted(interfaces.keys()):
                if interface in [
                    "org.freedesktop.DBus.Introspectable",
                    "org.freedesktop.DBus.Properties",
                ]:
                    continue
                print("    %s" % (interface))
                properties = interfaces[interface]
                for key in sorted(properties.keys()):
                    print("      %s = %s" % (key, properties[key]))


class Adapter:
    def __init__(self, teal, path, properties):
        self._teal = teal
        self._path = path
        self._properties = properties
        self._object = dbus.Interface(
            teal._bus.get_object("org.bluez", path), "org.bluez.Adapter1"
        )
        self._advertisement = None

    def __repr__(self):
        return "<tealblue.Adapter address=%s>" % (self._properties["Address"])

    def devices(self):
        """
        Returns the devices that BlueZ has discovered.
        """
        objects = self._teal._bluez.GetManagedObjects()
        for path in sorted(objects.keys()):
            interfaces = objects[path]
            if "org.bluez.Device1" not in interfaces:
                continue
            properties = interfaces["org.bluez.Device1"]
            yield Device(self._teal, path, properties)

    def scan(self, timeout_s):
        return Scanner(self._teal, self, self.devices(), timeout_s)

    @property
    def advertisement(self):
        if self._advertisement is None:
            self._advertisement = Advertisement(self._teal, self)
        return self._advertisement

    def advertise(self, enable):
        if enable:
            self.advertisement.enable()
        else:
            self.advertisement.disable()

    def advertise_data(
        self,
        local_name=None,
        service_data=None,
        service_uuids=None,
        manufacturer_data=None,
    ):
        self.advertisement.local_name = local_name
        self.advertisement.service_data = service_data
        self.advertisement.service_uuids = service_uuids
        self.advertisement.manufacturer_data = manufacturer_data


class Scanner:
    def __init__(self, teal, adapter, initial_devices, timeout_s):
        self._teal = teal
        self._adapter = adapter
        self._was_discovering = adapter._properties[
            "Discovering"
        ]  # TODO get current value, or watch property changes
        self._queue = queue.Queue()
        self.timeout_s = timeout_s
        for device in initial_devices:
            self._queue.put(device)

        def new_device(path, interfaces):
            if "org.bluez.Device1" not in interfaces:
                return
            if not path.startswith(self._adapter._path + "/"):
                return
            # properties = interfaces["org.bluez.Device1"]
            self._queue.put(Device(self._teal, path, interfaces["org.bluez.Device1"]))

        self._signal_receiver = self._teal._bus.add_signal_receiver(
            new_device,
            dbus_interface="org.freedesktop.DBus.ObjectManager",
            signal_name="InterfacesAdded",
        )
        if not self._was_discovering:
            self._adapter._object.StartDiscovery()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if not self._was_discovering:
            self._adapter._object.StopDiscovery()
        self._signal_receiver.remove()

    def __iter__(self):
        return self

    def __next__(self):
        try:
            return self._queue.get(timeout=self.timeout_s)
        except queue.Empty:
            raise StopIteration


class Device:
    def __init__(self, teal, path, properties):
        self._teal = teal
        self._path = path
        self._properties = properties
        self._services_resolved = threading.Event()
        self._services = None

        if properties["ServicesResolved"]:
            self._services_resolved.set()

        # Listen to device events (connect, disconnect, ServicesResolved, ...)
        self._device = dbus.Interface(
            teal._bus.get_object("org.bluez", path), "org.bluez.Device1"
        )
        self._device_props = dbus.Interface(
            self._device, "org.freedesktop.DBus.Properties"
        )
        self._signal_receiver = self._device_props.connect_to_signal(
            "PropertiesChanged",
            lambda itf, ch, inv: self._on_prop_changed(itf, ch, inv),
        )

    def __del__(self):
        self._signal_receiver.remove()

    def __repr__(self):
        return "<tealblue.Device address=%s name=%r>" % (self.address, self.name)

    def _on_prop_changed(self, properties, changed_props, invalidated_props):
        for key, value in changed_props.items():
            self._properties[key] = value

        if "ServicesResolved" in changed_props:
            if changed_props["ServicesResolved"]:
                self._services_resolved.set()
            else:
                self._services_resolved.clear()

    def _wait_for_discovery(self):
        # wait until ServicesResolved is True
        self._services_resolved.wait()

    def connect(self):
        self._device.Connect()

    def disconnect(self):
        self._device.Disconnect()

    def resolve_services(self):
        self._services_resolved.wait()

    @property
    def services(self):
        if not self._services_resolved.is_set():
            return None
        if self._services is None:
            self._services = {}
            objects = self._teal._bluez.GetManagedObjects()
            for path in sorted(objects.keys()):
                if not path.startswith(self._path + "/"):
                    continue
                if "org.bluez.GattService1" in objects[path]:
                    properties = objects[path]["org.bluez.GattService1"]
                    service = Service(self._teal, self, path, properties)
                    self._services[service.uuid] = service
                elif "org.bluez.GattCharacteristic1" in objects[path]:
                    properties = objects[path]["org.bluez.GattCharacteristic1"]
                    characterstic = Characteristic(self._teal, self, path, properties)
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
    def __init__(self, teal, device, path, properties):
        self._device = device
        self._teal = teal
        self._path = path
        self._properties = properties

        self.on_notify = None

        self._char = dbus.Interface(
            teal._bus.get_object("org.bluez", path), "org.bluez.GattCharacteristic1"
        )
        char_props = dbus.Interface(self._char, "org.freedesktop.DBus.Properties")
        self._signal_receiver = char_props.connect_to_signal(
            "PropertiesChanged",
            lambda itf, ch, inv: self._on_prop_changed(itf, ch, inv),
        )

    def __repr__(self):
        return "<tealblue.Characteristic device=%s uuid=%s>" % (
            self._device.address,
            self.uuid,
        )

    def __del__(self):
        self._signal_receiver.remove()

    def _on_prop_changed(self, properties, changed_props, invalidated_props):
        for key, value in changed_props.items():
            self._properties[key] = bytes(value)

        if "Value" in changed_props and self.on_notify is not None:
            self.on_notify(self, changed_props["Value"])

    def read(self):
        return bytes(self._char.ReadValue({}))

    def write(self, value, command=True):
        start = time.time()
        try:
            if command:
                self._char.WriteValue(value, {"type": "command"})
            else:
                self._char.WriteValue(value, {"type": "request"})

        except dbus.DBusException as e:
            if (
                e.get_dbus_name() == "org.bluez.Error.Failed"
                and e.get_dbus_message() == "Not connected"
            ):
                raise NotConnectedError()
            else:
                raise  # some other error

        # Workaround: if the write took very long, it is possible the connection
        # broke (without causing an exception). So check whether we are still
        # connected.
        # I think this is a bug in BlueZ.
        if time.time() - start > 0.5:
            if not self._device._device_props.Get("org.bluez.Device1", "Connected"):
                raise NotConnectedError()

    def start_notify(self):
        self._char.StartNotify()

    def stop_notify(self):
        self._char.StopNotify()

    @property
    def uuid(self):
        return str(self._properties["UUID"])


class Advertisement(dbus.service.Object):
    PATH = "/com/github/aykevl/pynus/advertisement"

    def __init__(self, teal, adapter):
        self._teal = teal
        self._adapter = adapter
        self._enabled = False
        self.service_uuids = None
        self.manufacturer_data = None
        self.solicit_uuids = None
        self.service_data = None
        self.local_name = None
        self.include_tx_power = None
        self._manager = dbus.Interface(
            teal._bus.get_object("org.bluez", self._adapter._path),
            "org.bluez.LEAdvertisingManager1",
        )
        self._adv_enabled = threading.Event()
        dbus.service.Object.__init__(self, teal._bus, self.PATH)

    def enable(self):
        if self._enabled:
            return
        self._manager.RegisterAdvertisement(
            dbus.ObjectPath(self.PATH),
            dbus.Dictionary({}, signature="sv"),
            reply_handler=self._cb_enabled,
            error_handler=self._cb_enabled_err,
        )
        self._adv_enabled.wait()
        self._adv_enabled.clear()

    def _cb_enabled(self):
        self._enabled = True
        if self._adv_enabled.is_set():
            raise RuntimeError("called enable() twice")
        self._adv_enabled.set()

    def _cb_enabled_err(self, err):
        self._enabled = False
        if self._adv_enabled.is_set():
            raise RuntimeError("called enable() twice")
        self._adv_enabled.set()

    def disable(self):
        if not self._enabled:
            return
        self._bus.UnregisterAdvertisement(self.PATH)
        self._enabled = False

    @property
    def enabled(self):
        return self._enabled

    @dbus.service.method(
        "org.freedesktop.DBus.Properties", in_signature="s", out_signature="a{sv}"
    )
    def GetAll(self, interface):
        print("GetAll")
        if interface != "org.bluez.LEAdvertisement1":
            raise DBusInvalidArgsException()

        try:
            properties = {
                "Type": dbus.String("peripheral"),
            }
            if self.service_uuids is not None:
                properties["ServiceUUIDs"] = dbus.Array(
                    map(format_uuid, self.service_uuids), signature="s"
                )
            if self.solicit_uuids is not None:
                properties["SolicitUUIDs"] = dbus.Array(
                    map(format_uuid, self.solicit_uuids), signature="s"
                )
            if self.manufacturer_data is not None:
                properties["ManufacturerData"] = dbus.Dictionary(
                    {k: v for k, v in self.manufacturer_data.items()}, signature="qv"
                )
            if self.service_data is not None:
                properties["ServiceData"] = dbus.Dictionary(
                    self.service_data, signature="sv"
                )
            if self.local_name is not None:
                properties["LocalName"] = dbus.String(self.local_name)
            if self.include_tx_power is not None:
                properties["IncludeTxPower"] = dbus.Boolean(self.include_tx_power)
        except Exception as e:
            print("err: ", e)
        print("properties:", properties)
        return properties

    @dbus.service.method(
        "org.bluez.LEAdvertisement1", in_signature="", out_signature=""
    )
    def Release(self):
        self._enabled = True
