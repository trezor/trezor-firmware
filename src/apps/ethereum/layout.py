from trezor import wire, ui
from trezor.utils import unimport, chunks
from trezor.messages import ButtonRequestType
from trezor.ui.text import Text
from apps.common.confirm import *
from . import networks


@unimport
async def confirm_tx(ctx, to, value, chain_id, token=None):
    content = Text('Confirm transaction', ui.ICON_RESET,
                   ui.BOLD, format_amount(value, token, chain_id),
                   ui.NORMAL, 'to',
                   ui.MONO, *split_address(to))  # todo no addres shown, why?
    return await confirm(ctx, content, ButtonRequestType.ConfirmOutput)


@unimport
async def confirm_fee(ctx, spending, fee, chain_id, token=None):
    content = Text('Confirm transaction', ui.ICON_RESET,
                   'Sending: %s' % format_amount(spending, token, chain_id),
                   'Fee: %s' % format_amount(fee, token, chain_id))
    return await hold_to_confirm(ctx, content, ButtonRequestType.SignTx)


@unimport
async def confirm_data(ctx, data, data_total):
    content = Text('Confirm data', ui.ICON_RESET,
                   ui.MONO, data[:16],  # todo nothing displayed?
                   'of total: ', data_total)
    return await confirm(ctx, content, ButtonRequestType.ConfirmOutput)


@unimport
async def confirm_fee(ctx, value, gas_price, gas_limit, token):
    content = Text('Confirm fee', ui.ICON_RESET,
                   'price:', ui.MONO, gas_price,  # todo wording
                   'limit:', ui.MONO, gas_limit,
                   'value: ', value)
    return await confirm(ctx, content, ButtonRequestType.ConfirmOutput)


def split_address(address):
    return chunks(address, 17)


def format_amount(value, token, chain_id):
    value = int.from_bytes(value, 'little')
    if token:
        suffix = token.ticker
        decimals = token.decimals
    elif value < 1e18:
        suffix = 'Wei'
        decimals = 0
    else:
        decimals = 18
        suffix = networks.suffix_by_chain_id(chain_id)

    return '%s %s' % (value // 10 ** decimals, suffix)
