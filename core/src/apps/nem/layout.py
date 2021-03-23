from trezor import ui
from trezor.enums import ButtonRequestType
from trezor.strings import format_amount
from trezor.ui.components.tt.text import Text

from apps.common.confirm import require_confirm, require_hold_to_confirm

from .helpers import NEM_MAX_DIVISIBILITY


async def require_confirm_text(ctx, action: str):
    text = Text("Confirm action", ui.ICON_SEND, ui.GREEN, new_lines=False)
    text.normal(action)
    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)


async def require_confirm_fee(ctx, action: str, fee: int):
    content = (
        ui.NORMAL,
        action,
        ui.BOLD,
        "%s XEM" % format_amount(fee, NEM_MAX_DIVISIBILITY),
    )
    await require_confirm_content(ctx, "Confirm fee", content)


async def require_confirm_content(ctx, headline: str, content: list):
    text = Text(headline, ui.ICON_SEND, ui.GREEN)
    text.normal(*content)
    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)


async def require_confirm_final(ctx, fee: int):
    text = Text("Final confirm", ui.ICON_SEND, ui.GREEN)
    text.normal("Sign this transaction")
    text.bold("and pay %s XEM" % format_amount(fee, NEM_MAX_DIVISIBILITY))
    text.normal("for network fee?")
    # we use SignTx, not ConfirmOutput, for compatibility with T1
    await require_hold_to_confirm(ctx, text, ButtonRequestType.SignTx)
