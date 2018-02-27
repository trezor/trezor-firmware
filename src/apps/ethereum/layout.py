from apps.common.confirm import *
from trezor import ui
from trezor.utils import chunks, format_amount
from trezor.messages import ButtonRequestType
from trezor.ui.text import Text
from ubinascii import hexlify
from . import networks


async def confirm_tx(ctx, to, value, chain_id, token=None):  # TODO: wording
    str_to = '0x' + hexlify(to).decode()  # TODO: use ethereum address format
    content = Text('Confirm transaction', ui.ICON_DEFAULT,
                   ui.BOLD, format_ethereum_amount(value, token, chain_id),
                   ui.NORMAL, 'to',
                   ui.MONO, *split_address(str_to))
    return await confirm(ctx, content, ButtonRequestType.SignTx)  # we use SignTx, not ConfirmOutput, for compatibility with T1


async def confirm_fee(ctx, spending, gas_price, gas_limit, chain_id, token=None):  # TODO: wording
    content = Text('Confirm fee', ui.ICON_DEFAULT,
                   'Sending: %s' % format_ethereum_amount(spending, token, chain_id),
                   'Gas: %s' % format_ethereum_amount(gas_price, token, chain_id),
                   'Limit: %s' % format_ethereum_amount(gas_limit, token, chain_id))
    return await hold_to_confirm(ctx, content, ButtonRequestType.SignTx)


async def confirm_data(ctx, data, data_total):  # TODO: wording
    str_data = hexlify(data[:8]).decode() + '..'
    content = Text('Confirm data:', ui.ICON_DEFAULT,
                   ui.MONO, str_data,
                   'Total: ', str(data_total) + 'B')
    return await confirm(ctx, content, ButtonRequestType.SignTx)  # we use SignTx, not ConfirmOutput, for compatibility with T1


def split_address(address):
    return chunks(address, 17)


def format_ethereum_amount(value, token, chain_id):
    value = int.from_bytes(value, 'big')
    if token:
        suffix = token['symbol']
        decimals = token['decimal']
    elif value < 1e18:
        suffix = 'Wei'
        decimals = 0
    else:
        decimals = 18
        suffix = networks.suffix_by_chain_id(chain_id)

    return '%s %s' % (format_amount(value, decimals), suffix)
