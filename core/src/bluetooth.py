from trezorio import ble
from typing import TYPE_CHECKING

from trezor import config

from apps.base import unlock_device

if TYPE_CHECKING:
    from trezor import protobuf, wire


class BleInterfaceInternal:
    def iface_num(self) -> int:
        return 16

    def write(self, msg: bytes) -> int:
        return ble.write_int(self, msg)


class BleInterfaceExternal:
    def iface_num(self) -> int:
        return 17

    def write(self, msg: bytes) -> int:
        return ble.write_ext(self, msg)


def find_ble_int_handler(iface, msg_type) -> wire.Handler | None:
    from trezor.enums import MessageType

    modname = None

    if msg_type == MessageType.PairingRequest:
        modname = "apps.management.ble.pairing_request"
    if msg_type == MessageType.RepairRequest:
        modname = "apps.management.ble.repair_request"
    if msg_type == MessageType.ComparisonRequest:
        modname = "apps.management.ble.comparison_request"

    if modname is not None:
        try:
            handler_name = modname[modname.rfind(".") + 1 :]
            module = __import__(modname, None, None, (handler_name,), 0)
            return getattr(module, handler_name)
        except ValueError:
            return None

    return None


def int_find_handler(
    iface: wire.WireInterface, msg_type: int
) -> wire.Handler[wire.Msg] | None:

    orig_handler = find_ble_int_handler(iface, msg_type)

    if config.is_unlocked():
        return orig_handler
    else:
        if orig_handler is None:
            return None

        async def wrapper(ctx: wire.Context, msg: wire.Msg) -> protobuf.MessageType:
            await unlock_device(ctx, True)
            return await orig_handler(ctx, msg)

    return wrapper


# interface used for trezor wire protocol
iface_ble_int = BleInterfaceInternal()
iface_ble_ext = BleInterfaceExternal()
