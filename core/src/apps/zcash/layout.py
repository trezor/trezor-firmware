from trezor import strings, ui
from trezor.enums import ButtonRequestType
from trezor.ui.layouts import confirm_action

async def require_confirm_export_fvk(ctx):
    await confirm_action(
        ctx,
        "get_full_viewing_key",
        "Confirm export",
        description="Do you really want to export Full Viewing Key?",
        icon=ui.ICON_SEND,
        icon_color=ui.GREEN,
        br_code=ButtonRequestType.SignTx,
    )

async def require_confirm_export_ivk(ctx):
    await confirm_action(
        ctx,
        "get_incoming_viewing_key",
        "Confirm export",
        description="Do you really want to export Incoming Viewing Key?",
        icon=ui.ICON_SEND,
        icon_color=ui.GREEN,
        br_code=ButtonRequestType.SignTx,
    )