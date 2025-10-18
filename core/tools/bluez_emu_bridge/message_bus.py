import logging
from typing import Any

from dbus_fast import aio
from dbus_fast.message import Message
from dbus_fast.service import ServiceInterface

LOG = logging.getLogger(__name__)


class MessageBus(aio.MessageBus):
    def _emit_interface_added(self, path: str, interface: str) -> None:
        if self._disconnected:
            return

        def get_properties_callback(
            interface: ServiceInterface,
            result: Any,
            user_data: Any,
            e: Exception | None,
        ) -> None:
            if e is not None:
                try:
                    raise e
                except Exception:
                    logging.error(
                        "An exception ocurred when emitting ObjectManager.InterfacesAdded for %s. "
                        "Some properties will not be included in the signal.",
                        interface.name,
                        exc_info=True,
                    )

            body = {interface.name: result}

            # BlueZ's InterfacesAdded signal has different path in the message body and
            # in the metadata. However with dbus-fast they are always the same, and such
            # signal will get ignored by btleplug and other BlueZ clients. Patch it here.
            envelope_path = path
            if "/dev_" in envelope_path:
                envelope_path = "/"
                LOG.debug(
                    f"InterfacesAdded: replacing path {path} with {envelope_path}"
                )

            self.send(
                Message.new_signal(
                    path=envelope_path,
                    interface="org.freedesktop.DBus.ObjectManager",
                    member="InterfacesAdded",
                    signature="oa{sa{sv}}",
                    body=[path, body],
                )
            )

        ServiceInterface._get_all_property_values(interface, get_properties_callback)
