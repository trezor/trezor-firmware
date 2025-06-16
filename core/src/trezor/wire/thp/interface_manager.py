from typing import TYPE_CHECKING

import usb
from trezor import utils

if utils.USE_BLE:
    import trezorble as ble

    _WIRE_INTERFACE_BLE = b"\x02"


_WIRE_INTERFACE_USB = b"\x01"

if TYPE_CHECKING:
    from trezorio import WireInterface


def decode_iface(cached_iface: bytes | None) -> WireInterface:
    """Decode the cached wire interface."""
    if cached_iface == _WIRE_INTERFACE_USB:
        return usb.iface_wire
    if utils.USE_BLE:
        if cached_iface == _WIRE_INTERFACE_BLE:
            return ble.interface

    raise Exception("Unknown WireInterface")


def encode_iface(iface: WireInterface) -> bytes:
    """Encode wire interface into bytes."""
    if iface is usb.iface_wire:
        return _WIRE_INTERFACE_USB
    if utils.USE_BLE:
        if iface is ble.interface:
            return _WIRE_INTERFACE_BLE
    raise Exception("Unknown WireInterface")
