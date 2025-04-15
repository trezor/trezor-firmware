from typing import TYPE_CHECKING

import trezorble as ble
from trezor import TR

if TYPE_CHECKING:
    from trezor.messages import BleUnpair


async def unpair(msg: BleUnpair) -> None:
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_action
    from trezor.wire.context import NoWireContext, get_context

    if msg.all:
        await confirm_action("erase bonds", TR.ble__unpair_title, TR.ble__unpair_all)
    else:
        await confirm_action("unpair", TR.ble__unpair_title, TR.ble__unpair_current)

    # NOTE: refactor into ctx.maybe_write if we end up doing this in multiple places
    try:
        ctx = get_context()
    except NoWireContext:
        pass
    else:
        await ctx.write(Success(message="Erasing..."))

    if msg.all:
        ble.erase_bonds()
    else:
        ble.unpair()
