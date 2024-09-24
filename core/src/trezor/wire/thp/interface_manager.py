from typing import TYPE_CHECKING

import usb

_MOCK_INTERFACE_HID = b"\x00"
_WIRE_INTERFACE_USB = b"\x01"

if TYPE_CHECKING:
    from trezorio import WireInterface


def decode_iface(cached_iface: bytes) -> WireInterface:
    """Decode the cached wire interface."""
    if cached_iface == _WIRE_INTERFACE_USB:
        iface = usb.iface_wire
        if iface is None:
            raise RuntimeError("There is no valid USB WireInterface")
        return iface
    # TODO implement bluetooth interface
    raise Exception("Unknown WireInterface")


def encode_iface(iface: WireInterface) -> bytes:
    """Encode wire interface into bytes."""
    if iface is usb.iface_wire:
        return _WIRE_INTERFACE_USB
    # TODO implement bluetooth interface
    if __debug__:
        return _MOCK_INTERFACE_HID
    raise Exception("Unknown WireInterface")