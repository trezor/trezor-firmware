from apps.common.confirm import require_confirm, require_hold_to_confirm
from apps.wallet.get_public_key import _show_pubkey
from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.ui.text import Text
from trezor.utils import chunks

from .helpers import get_vote_tx_text


async def require_confirm_tx(ctx, to, value):
    content = Text('Confirm sending', ui.ICON_SEND,
                   ui.BOLD, format_amount(value),
                   ui.NORMAL, 'to',
                   ui.MONO, *split_address(to),
                   icon_color=ui.GREEN)
    return await require_confirm(ctx, content, ButtonRequestType.SignTx)


async def require_confirm_delegate_registration(ctx, delegate_name):
    content = Text('Confirm transaction', ui.ICON_SEND,
                   'Do you really want to',
                   'register a delegate?',
                   ui.BOLD, *chunks(delegate_name, 20),
                   icon_color=ui.GREEN)
    return await require_confirm(ctx, content, ButtonRequestType.SignTx)


async def require_confirm_vote_tx(ctx, votes):
    content = Text('Confirm transaction', ui.ICON_SEND,
                   *get_vote_tx_text(votes),
                   icon_color=ui.GREEN)
    return await require_confirm(ctx, content, ButtonRequestType.SignTx)


async def require_confirm_public_key(ctx, public_key):
    return await _show_pubkey(ctx, public_key)


async def require_confirm_multisig(ctx, multisignature):
    content = Text('Confirm transaction', ui.ICON_SEND,
                   ('Keys group length: %s' % len(multisignature.keys_group)),
                   ('Life time: %s' % multisignature.life_time),
                   ('Min: %s' % multisignature.min),
                   icon_color=ui.GREEN)
    return await require_confirm(ctx, content, ButtonRequestType.SignTx)


async def require_confirm_fee(ctx, value, fee):
    content = Text('Confirm transaction', ui.ICON_SEND,
                   ui.BOLD, format_amount(value),
                   ui.NORMAL, 'fee:',
                   ui.BOLD, format_amount(fee),
                   icon_color=ui.GREEN)
    await require_hold_to_confirm(ctx, content, ButtonRequestType.ConfirmOutput)


def format_amount(value):
    return '%s LSK' % (int(value) / 100000000)


def split_address(address):
    return chunks(address, 16)
