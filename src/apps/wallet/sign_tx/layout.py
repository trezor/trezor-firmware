from ubinascii import hexlify
from trezor import ui
from trezor.utils import chunks, format_amount
from trezor.ui.text import Text
from trezor.messages import ButtonRequestType
from trezor.messages import OutputScriptType
from apps.common.confirm import confirm
from apps.common.confirm import hold_to_confirm
from apps.wallet.sign_tx import addresses


def format_coin_amount(amount, coin):
    return '%s %s' % (format_amount(amount, 8), coin.coin_shortcut)


def split_address(address):
    return chunks(address, 17)


def split_op_return(data):
    return chunks(data, 18)


async def confirm_output(ctx, output, coin):
    if output.script_type == OutputScriptType.PAYTOOPRETURN:
        data = hexlify(output.op_return_data).decode()
        if len(data) >= 18 * 5:
            data = data[:(18 * 5 - 3)] + '...'
        text = Text('OP_RETURN', ui.ICON_SEND, icon_color=ui.GREEN)
        text.mono(*split_op_return(data))
    else:
        address = output.address
        address_short = addresses.address_short(coin, address)
        text = Text('Confirm sending', ui.ICON_SEND, icon_color=ui.GREEN)
        text.type(format_coin_amount(output.amount, coin) + ' to')
        text.mono(*split_address(address_short))
    return await confirm(ctx, text, ButtonRequestType.ConfirmOutput)


async def confirm_total(ctx, spending, fee, coin):
    text = Text('Confirm transaction', ui.ICON_SEND, icon_color=ui.GREEN)
    text.type('Total amount:')
    text.bold(format_coin_amount(spending, coin))
    text.type('including fee:')
    text.bold(format_coin_amount(fee, coin))
    return await hold_to_confirm(ctx, text, ButtonRequestType.SignTx)


async def confirm_feeoverthreshold(ctx, fee, coin):
    text = Text('High fee', ui.ICON_SEND, icon_color=ui.GREEN)
    text.type('The fee of')
    text.bold(format_coin_amount(fee, coin))
    text.type('is unexpectedly high.', 'Continue?')
    return await confirm(ctx, text, ButtonRequestType.FeeOverThreshold)


async def confirm_foreign_address(ctx, address_n, coin):
    text = Text('Confirm sending', ui.ICON_SEND, icon_color=ui.RED)
    text.type(
        'Trying to spend',
        'coins from another chain.',
        'Continue?')
    return await confirm(ctx, text, ButtonRequestType.SignTx)
