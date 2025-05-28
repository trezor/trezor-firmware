import time

import trezorui_api
from trezor import utils, workflow

from .. import context
from ..protocol_common import Context

if __debug__:
    from .. import wire_log as log


async def show_autoconnect_credential_confirmation_screen(
    ctx: Context, host_name: str | None
) -> None:
    from trezor.enums import ButtonRequestType
    from trezor.ui.layouts.common import interact

    # TODO FIXME
    _hotfix(ctx)

    await interact(
        trezorui_api.confirm_action(
            title="Autoconnect credential",
            action=f"Do you want to pair with {host_name} without confirmation?",
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
        if __debug__ and utils.ALLOW_DEBUG_MESSAGES:
            log.debug(
                __name__,
                ctx.iface,
                "Hotfix for current context being destroyed by workflow.close_others",
            )
    # --- HOTFIX END ---
