from typing import TYPE_CHECKING

import trezorble as ble
from trezor import TR

if TYPE_CHECKING:
    from trezor.messages import BleUnpair


async def unpair(msg: BleUnpair) -> None:
    from trezor.messages import Success
    from trezor.ui.layouts import show_success, show_warning
    from trezor.wire.context import NoWireContext, get_context

    if msg.all:
        br_name = "erase bonds"
        template = TR.ble__all_devices
        success = TR.ble__all_forgotten
    else:
        br_name = "unpair"
        template = TR.ble__connected_device
        success = TR.ble__current_forgotten

    await show_warning(
        br_name,
        TR.ble__forget_template.format(template),
        TR.words__are_you_sure,
        button=TR.buttons__confirm,
    )
    await show_success(
        br_name,
        success,
        button=TR.buttons__close,
    )

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
