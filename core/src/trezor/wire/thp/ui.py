import time

import trezorui_api
from trezor import workflow

from .. import context
from ..protocol_common import Context

if __debug__:
    from trezor import log


async def show_autoconnect_credential_confirmation_screen(
    ctx: Context,
    host_name: str | None,
    device_name: str | None = None,
) -> None:
    from trezor.enums import ButtonRequestType
    from trezor.ui.layouts.common import interact

    # TODO FIXME
    _hotfix(ctx)

    if not device_name:
        action_string = f"Allow {host_name} to connect automatically to this Trezor?"
    else:
        action_string = f"Allow {host_name} on {device_name} to connect automatically to this Trezor?"

    await interact(
        trezorui_api.confirm_action(
            title="Autoconnect credential",
            action=action_string,
            description=None,
        ),
        br_name="thp_autoconnect_credential_request",
        br_code=ButtonRequestType.Other,
    )


def _hotfix(ctx: Context) -> None:
    # TODO FIXME
    # The subsequent code is a hotfix for the following issue:
    #
    # 1. `interact` - on lines `result = await interact(` - calls `workflow.close_others` and `_button_request`
    # 2. `workflow.close_others` may result in clearing of `context.CURRENT_CONTEXT`
    # 3. `_button_request` uses `context.maybe_call` - sending of button request is ommited
    #    when `context.CURRENT_CONTEXT` is `None`
    # 4. test gets stuck on the pairing dialog screen
    #
    # The hotfix performs `workflow.close_others()` and in case of clearing of `context.CURRENT_CONTEXT`, it
    # is set to a functional value (`self`)

    workflow.close_others()
    try:
        _ = context.get_context()
    except RuntimeError:
        time.sleep(0.1)
        context.CURRENT_CONTEXT = ctx
        if __debug__:
            log.debug(
                __name__,
                "Hotfix for current context being destroyed by workflow.close_others",
                iface=ctx.iface,
            )
    # --- HOTFIX END ---
