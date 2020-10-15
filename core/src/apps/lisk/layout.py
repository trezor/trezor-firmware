from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.strings import format_amount
from trezor.ui.components.tt.text import Text
from trezor.utils import chunks

from apps.common.confirm import require_confirm, require_hold_to_confirm
from apps.common.layout import show_pubkey, split_address

from .helpers import get_vote_tx_text


async def require_confirm_tx(ctx, to, value):
    text = Text("Confirm sending", ui.ICON_SEND, ui.GREEN)
    text.bold(format_coin_amount(value))
    text.normal("to")
    text.mono(*split_address(to))
    await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_delegate_registration(ctx, delegate_name):
    text = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    text.normal("Do you really want to")
    text.normal("register a delegate?")
    text.bold(*chunks(delegate_name, 20))
    await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_vote_tx(ctx, votes):
    text = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    text.normal(*get_vote_tx_text(votes))
    await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_public_key(ctx, public_key):
    return await show_pubkey(ctx, public_key)


async def require_confirm_multisig(ctx, multisignature):
    text = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    text.normal("Keys group length: %s" % len(multisignature.keys_group))
    text.normal("Life time: %s" % multisignature.life_time)
    text.normal("Min: %s" % multisignature.min)
    await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_fee(ctx, value, fee):
    text = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    text.bold(format_coin_amount(value))
    text.normal("fee:")
    text.bold(format_coin_amount(fee))
    await require_hold_to_confirm(ctx, text, ButtonRequestType.ConfirmOutput)


def format_coin_amount(value):
    return "%s LSK" % format_amount(value, 8)
