from trezor import ui
from trezor.utils import chunks
from trezor.ui.text import Text
from trezor.messages import ButtonRequestType
from apps.common.confirm import confirm
from apps.common.confirm import hold_to_confirm


def format_amount(amount, coin):
    return '%s %s' % (amount / 1e8, coin.coin_shortcut)


def split_address(address):
    return chunks(address, 17)


async def confirm_output(ctx, output, coin):
    # TODO: handle OP_RETURN correctly
    content = Text('Confirm output', ui.ICON_RESET,
                   ui.BOLD, format_amount(output.amount, coin),
                   ui.NORMAL, 'to',
                   ui.MONO, *split_address(output.address))
    return await confirm(ctx, content, ButtonRequestType.ConfirmOutput)


async def confirm_total(ctx, spending, fee, coin):
    content = Text('Confirm transaction', ui.ICON_RESET,
                   'Sending: %s' % format_amount(spending, coin),
                   'Fee: %s' % format_amount(fee, coin))
    return await hold_to_confirm(ctx, content, ButtonRequestType.SignTx)


async def confirm_feeoverthreshold(ctx, fee, coin):
    content = Text('Confirm high fee:', ui.ICON_RESET,
                   ui.BOLD, format_amount(fee, coin))
    return await confirm(ctx, content, ButtonRequestType.FeeOverThreshold)
