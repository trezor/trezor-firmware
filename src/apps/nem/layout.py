from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.ui.text import Text
from trezor.utils import chunks, format_amount, split_words

from .helpers import NEM_MAX_DIVISIBILITY

from apps.common.confirm import require_confirm, require_hold_to_confirm


async def require_confirm_text(ctx, action: str):
    words = split_words(action, 18)
    await require_confirm_content(ctx, "Confirm action", words)


async def require_confirm_fee(ctx, action: str, fee: int):
    content = (
        ui.NORMAL,
        action,
        ui.BOLD,
        "%s XEM" % format_amount(fee, NEM_MAX_DIVISIBILITY),
    )
    await require_confirm_content(ctx, "Confirm fee", content)


async def require_confirm_content(ctx, headline: str, content: list):
    text = Text(headline, ui.ICON_SEND, icon_color=ui.GREEN)
    text.normal(*content)
    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)


async def require_confirm_final(ctx, fee: int):
    text = Text("Final confirm", ui.ICON_SEND, icon_color=ui.GREEN)
    text.normal("Sign this transaction")
    text.bold("and pay %s XEM" % format_amount(fee, NEM_MAX_DIVISIBILITY))
    text.normal("for network fee?")
    # we use SignTx, not ConfirmOutput, for compatibility with T1
    await require_hold_to_confirm(ctx, text, ButtonRequestType.SignTx)


def split_address(address: str):
    return chunks(address, 17)


def trim(payload: str, length: int) -> str:
    if len(payload) > length:
        return payload[:length] + ".."
    return payload
