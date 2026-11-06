"""Who is calling the WARD service, as established by the firmware.

An entry's domain (app_id) and device slot are part of its entry_key, so whoever names
them decides whose entries a read or write touches. That is never the caller's to say:
apps on the Trezor -- core apps, and third-party apps that are untrusted -- reach WARD only
through the WARD service, which derives the domain from the caller's identity and allows a
device slot other than 0x00 to core apps only. The host is not an app; what it sends is
served under one domain the service fixes for host-driven address labels.

A WardCaller is therefore created only here and by firmware code -- never from a field of
a message.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from buffer_types import AnyBytes

_EXTAPP_PREFIX = b"ext:"


class WardCaller:
    """A caller of the WARD service: the domain its entries live in, and whether it is a
    core app (only core apps may use a device slot other than 0x00)."""

    __slots__ = ("app_id", "core")

    def __init__(self, app_id: bytes, core: bool) -> None:
        if core and app_id.startswith(_EXTAPP_PREFIX):
            raise ValueError("core WARD domains cannot use the extapp namespace")
        self.app_id = app_id
        self.core = core

    def device_slot(self, device_id: int) -> int:
        """`device_id` if this caller may use it, else raise: slot 0x00 is open to every
        caller, any other slot only to core apps."""
        from trezor.wire import DataError

        if device_id == 0:
            return 0
        if not self.core or not 0 < device_id <= 0xFF:
            raise DataError("WARD: device slot not available to this caller")
        return device_id


# The domain the WARD service assigns to everything the HOST sends (WARDQueueUpdate,
# WARDLookup, DisplayAddress labels). The value is kept from the earlier host-chosen
# scheme so existing trees and the offline-cache mapping stay valid.
ADDRESS_LABELS = WardCaller(b"bitcoin", core=False)

# Core apps that call the WARD service on the device.
DISPLAY_ADDRESS = WardCaller(b"display_address", core=True)


def extapp_caller(image_id: AnyBytes) -> WardCaller:
    """The caller for a third-party app, from the id of its VERIFIED image (the loader
    checks it against the signed app root). Its own namespace, so it can never collide
    with a core domain or another app's. Unused until extapps get an IPC path to the
    WARD service."""
    return WardCaller(_EXTAPP_PREFIX + bytes(image_id), core=False)


def host_caller(
    app_id: str | None, key_type: str | None, device_id: int | None
) -> WardCaller:
    """The caller for a host message. The scope fields stay on the wire for
    compatibility, but the host does not choose them: each must be absent or equal to
    what the service fixes for host-driven labels, or the request is refused."""
    from trezor.wire import DataError

    if app_id and app_id.encode() != ADDRESS_LABELS.app_id:
        raise DataError("WARD: the domain is chosen by the WARD service")
    if key_type and key_type != "address":
        raise DataError("WARD: the key type is chosen by the WARD service")
    if device_id:
        raise DataError("WARD: the device slot is chosen by the WARD service")
    return ADDRESS_LABELS
