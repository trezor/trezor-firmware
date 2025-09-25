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
        from apps.thp.credential_manager import invalidate_cred_auth_key

        # THP credentials should be invalidated when "Forget all" is handled.
        # Otherwise, the device will not ask for THP confirmation after reconnecting.
        invalidate_cred_auth_key()
        ble.erase_bonds()
    else:
        ble.unpair(msg.addr)

    if msg.all:
        await show_success(
            br_name=None,
            content=TR.ble__forget_all_success,
            button=TR.buttons__close,
        )
    else:
        await show_success(
            br_name=None,
            content=TR.ble__forget_this_success,
            button=TR.buttons__close,
        )
