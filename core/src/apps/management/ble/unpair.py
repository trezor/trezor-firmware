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
        await show_warning(
            "prompt_all_devices_unpair",
            TR.ble__forget_all_devices,
            TR.ble__forget_all_description,
            TR.buttons__confirm,
        )
    else:
        await show_warning(
            "prompt_device_unpair",
            TR.ble__forget_this_device,
            TR.ble__forget_this_description,
            TR.buttons__confirm,
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
    elif msg.addr is not None:
        ble.unpair(msg.addr)
    else:
        ble.unpair()

    if msg.all:
        await show_success(
            br_name="device_unpair_all_success",
            content=TR.ble__forget_all_success,
            button=TR.buttons__close,
        )
    else:
        await show_success(
            br_name="device_unpair_success",
            content=TR.ble__forget_this_device,
            button=TR.buttons__close,
        )
