from trezorio import ble
from typing import TYPE_CHECKING

from trezor import TR

if TYPE_CHECKING:
    from trezor.messages import BleUnpair


async def unpair(msg: BleUnpair) -> None:
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_action
    from trezor.wire.context import get_context

    if msg.all:
        await confirm_action("erase bonds", TR.ble__unpair_title, TR.ble__unpair_all)
    else:
        await confirm_action("unpair", TR.ble__unpair_title, TR.ble__unpair_current)

    try:
        ctx = get_context()
        await ctx.write(Success(message="Erasing.."))
    except RuntimeError:  # TODO newtype?
        pass

    if msg.all:
        ble.erase_bonds()
    else:
        ble.unpair()
