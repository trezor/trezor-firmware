from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.wire import Context


async def require_get_public_key(ctx: Context, public_key: str) -> None:
    from trezor.ui.layouts import show_pubkey

    await show_pubkey(ctx, public_key)


async def require_sign_tx(ctx: Context, num_actions: int) -> None:
    from trezor.enums import ButtonRequestType
    from trezor.strings import format_plural
    from trezor.ui.layouts import confirm_action

    await confirm_action(
        ctx,
        "confirm_tx",
        "Sign transaction",
        description="You are about to sign {}.",
        description_param=format_plural("{count} {plural}", num_actions, "action"),
        br_code=ButtonRequestType.SignTx,
    )
