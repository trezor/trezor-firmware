from trezor import ui, wire
from trezor.enums import ButtonRequestType
from trezor.strings import format_plural
from trezor.ui.layouts import confirm_action, show_pubkey


async def require_get_public_key(ctx: wire.Context, public_key: str) -> None:
    await show_pubkey(public_key)


async def require_sign_tx(num_actions: int) -> None:
    await confirm_action(
        "confirm_tx",
        title="Sign transaction",
        description="You are about to sign {}.",
        description_param=format_plural("{count} {plural}", num_actions, "action"),
        icon=ui.ICON_SEND,
        icon_color=ui.GREEN,
        br_code=ButtonRequestType.SignTx,
    )
