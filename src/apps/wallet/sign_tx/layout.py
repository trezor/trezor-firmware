from ubinascii import hexlify
from trezor import ui
from trezor.utils import chunks, format_amount
from trezor.ui.text import Text
from trezor.messages import ButtonRequestType
from trezor.messages import OutputScriptType
from apps.common.confirm import confirm
from apps.common.confirm import hold_to_confirm


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
        content = Text('OP_RETURN', ui.ICON_SEND,
                       ui.MONO, *split_op_return(data), icon_color=ui.GREEN)
    else:
        address = output.address
        address_short = address[len(coin.cashaddr_prefix) + 1:] if coin.cashaddr_prefix is not None else address
        content = Text('Confirm sending', ui.ICON_SEND,
                       ui.NORMAL, format_coin_amount(output.amount, coin) + ' to',
                       ui.MONO, *split_address(address_short), icon_color=ui.GREEN)
    return await confirm(ctx, content, ButtonRequestType.ConfirmOutput)


async def confirm_total(ctx, spending, fee, coin):
    content = Text('Confirm transaction', ui.ICON_SEND,
                   'Total amount:',
                   ui.BOLD, format_coin_amount(spending, coin),
                   ui.NORMAL, 'including fee:',
                   ui.BOLD, format_coin_amount(fee, coin), icon_color=ui.GREEN)
    return await hold_to_confirm(ctx, content, ButtonRequestType.SignTx)


async def confirm_feeoverthreshold(ctx, fee, coin):
    content = Text('High fee', ui.ICON_SEND,
                   'The fee of',
                   ui.BOLD, format_coin_amount(fee, coin),
                   ui.NORMAL, 'is unexpectedly high.',
                   'Continue?', icon_color=ui.GREEN)

    return await confirm(ctx, content, ButtonRequestType.FeeOverThreshold)
