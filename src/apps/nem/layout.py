from apps.common.confirm import *
from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.ui.text import Text
from trezor.utils import chunks, format_amount, split_words
from .helpers import *


async def require_confirm_text(ctx, action: str):
    await require_confirm_content(ctx, 'Confirm action', split_words(action, 18))


async def require_confirm_fee(ctx, action: str, fee: int):
    content = [ui.NORMAL, action,
               ui.BOLD, format_amount(fee, NEM_MAX_DIVISIBILITY) + ' XEM']
    await require_confirm_content(ctx, 'Confirm fee', content)


async def require_confirm_content(ctx, headline: str, content: []):
    text = Text(headline, ui.ICON_SEND,
                *content,
                icon_color=ui.GREEN)
    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)


async def require_confirm_final(ctx, fee: int):
    content = Text('Final confirm', ui.ICON_SEND,
                   ui.NORMAL, 'Sign this transaction',
                   ui.BOLD, 'and pay ' + format_amount(fee, NEM_MAX_DIVISIBILITY) + ' XEM',
                   ui.NORMAL, 'for network fee?',
                   icon_color=ui.GREEN)
    await require_hold_to_confirm(ctx, content, ButtonRequestType.SignTx)  # we use SignTx, not ConfirmOutput, for compatibility with T1


def split_address(data):
    return chunks(data, 17)


def trim(payload: str, length: int) -> str:
    if len(payload) > length:
        return payload[:length] + '..'
    return payload
