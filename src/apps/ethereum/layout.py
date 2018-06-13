from ubinascii import hexlify

from trezor import ui
from trezor.utils import chunks, format_amount
from trezor.messages import ButtonRequestType
from trezor.ui.text import Text

from apps.common.confirm import require_confirm, require_hold_to_confirm
from apps.ethereum import networks, tokens
from apps.ethereum.get_address import _ethereum_address_hex


async def require_confirm_tx(ctx, to, value, chain_id, token=None, tx_type=None):
    if to:
        str_to = _ethereum_address_hex(to, networks.by_chain_id(chain_id))
    else:
        str_to = 'new contract?'
    content = Text('Confirm sending', ui.ICON_SEND,
                   ui.BOLD, format_ethereum_amount(value, token, chain_id, tx_type),
                   ui.NORMAL, 'to',
                   ui.MONO, *split_address(str_to),
                   icon_color=ui.GREEN)
    await require_confirm(ctx, content, ButtonRequestType.SignTx)  # we use SignTx, not ConfirmOutput, for compatibility with T1


async def require_confirm_fee(ctx, spending, gas_price, gas_limit, chain_id, token=None, tx_type=None):
    content = Text('Confirm transaction', ui.ICON_SEND,
                   ui.BOLD, format_ethereum_amount(spending, token, chain_id, tx_type),
                   ui.NORMAL, 'Gas price:',
                   ui.BOLD, format_ethereum_amount(gas_price, None, chain_id, tx_type),
                   ui.NORMAL, 'Maximum fee:',
                   ui.BOLD, format_ethereum_amount(gas_price * gas_limit, None, chain_id, tx_type),
                   icon_color=ui.GREEN)
    await require_hold_to_confirm(ctx, content, ButtonRequestType.SignTx)


def split_data(data):
    return chunks(data, 18)


async def require_confirm_data(ctx, data, data_total):
    str_data = hexlify(data[:36]).decode()
    if data_total > 36:
        str_data = str_data[:-2] + '..'
    content = Text('Confirm data', ui.ICON_SEND,
                   ui.BOLD, 'Size: %d bytes' % data_total,
                   ui.MONO, *split_data(str_data),
                   icon_color=ui.GREEN)
    await require_confirm(ctx, content, ButtonRequestType.SignTx)  # we use SignTx, not ConfirmOutput, for compatibility with T1


def split_address(address):
    return chunks(address, 17)


def format_ethereum_amount(value: int, token, chain_id: int, tx_type=None):
    if token:
        if token is tokens.UNKNOWN_TOKEN:
            return 'Unknown token value'
        suffix = token[2]
        decimals = token[3]
    else:
        suffix = networks.shortcut_by_chain_id(chain_id, tx_type)
        decimals = 18

    if value <= 1e9:
        suffix = 'Wei ' + suffix
        decimals = 0

    return '%s %s' % (format_amount(value, decimals), suffix)
