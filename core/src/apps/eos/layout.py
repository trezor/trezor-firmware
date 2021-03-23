from trezor import ui, wire
from trezor.enums import ButtonRequestType
from trezor.ui.components.tt.text import Text

from apps.common.confirm import require_confirm


async def require_get_public_key(ctx: wire.Context, public_key: str) -> None:
    text = Text("Confirm public key", ui.ICON_RECEIVE, ui.GREEN)
    text.normal(public_key)
    await require_confirm(ctx, text, ButtonRequestType.PublicKey)


async def require_sign_tx(ctx: wire.Context, num_actions: int) -> None:
    text = Text("Sign transaction", ui.ICON_SEND, ui.GREEN)
    text.normal("You are about")
    text.normal("to sign {}".format(num_actions))
    text.normal("action(s).")
    await require_confirm(ctx, text, ButtonRequestType.SignTx)
