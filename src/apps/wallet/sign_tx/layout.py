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


async def confirm_output(ctx, output, coin):
    if output.script_type == OutputScriptType.PAYTOOPRETURN:
        address = 'OP_RETURN'  # TODO: handle OP_RETURN correctly
    else:
        address = output.address
    content = Text('Confirm output', ui.ICON_DEFAULT,
                   ui.BOLD, format_coin_amount(output.amount, coin),
                   ui.NORMAL, 'to',
                   ui.MONO, *split_address(address))
    return await confirm(ctx, content, ButtonRequestType.ConfirmOutput)


async def confirm_total(ctx, spending, fee, coin):
    content = Text('Confirm transaction', ui.ICON_DEFAULT,
                   'Sending: %s' % format_coin_amount(spending, coin),
                   'Fee: %s' % format_coin_amount(fee, coin))
    return await hold_to_confirm(ctx, content, ButtonRequestType.SignTx)


async def confirm_feeoverthreshold(ctx, fee, coin):
    content = Text('Confirm high fee:', ui.ICON_DEFAULT,
                   ui.BOLD, format_coin_amount(fee, coin))
    return await confirm(ctx, content, ButtonRequestType.FeeOverThreshold)
