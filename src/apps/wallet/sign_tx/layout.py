from ubinascii import hexlify

from trezor import ui
from trezor.messages import ButtonRequestType, OutputScriptType
from trezor.ui.text import Text
from trezor.utils import chunks, format_amount

from apps.common.confirm import confirm, hold_to_confirm
from apps.wallet.sign_tx import addresses


def format_coin_amount(amount, coin):
    return "%s %s" % (format_amount(amount, 8), coin.coin_shortcut)


def split_address(address):
    return chunks(address, 17)


def split_op_return(data):
    return chunks(data, 18)


async def confirm_output(ctx, output, coin):
    if output.script_type == OutputScriptType.PAYTOOPRETURN:
        data = hexlify(output.op_return_data).decode()
        if len(data) >= 18 * 5:
            data = data[: (18 * 5 - 3)] + "..."
        text = Text("OP_RETURN", ui.ICON_SEND, icon_color=ui.GREEN)
        text.mono(*split_op_return(data))
    else:
        address = output.address
        address_short = addresses.address_short(coin, address)
        text = Text("Confirm sending", ui.ICON_SEND, icon_color=ui.GREEN)
        text.normal(format_coin_amount(output.amount, coin) + " to")
        text.mono(*split_address(address_short))
    return await confirm(ctx, text, ButtonRequestType.ConfirmOutput)


async def confirm_total(ctx, spending, fee, coin):
    text = Text("Confirm transaction", ui.ICON_SEND, icon_color=ui.GREEN)
    text.normal("Total amount:")
    text.bold(format_coin_amount(spending, coin))
    text.normal("including fee:")
    text.bold(format_coin_amount(fee, coin))
    return await hold_to_confirm(ctx, text, ButtonRequestType.SignTx)


async def confirm_feeoverthreshold(ctx, fee, coin):
    text = Text("High fee", ui.ICON_SEND, icon_color=ui.GREEN)
    text.normal("The fee of")
    text.bold(format_coin_amount(fee, coin))
    text.normal("is unexpectedly high.", "Continue?")
    return await confirm(ctx, text, ButtonRequestType.FeeOverThreshold)


async def confirm_foreign_address(ctx, address_n, coin):
    text = Text("Confirm sending", ui.ICON_SEND, icon_color=ui.RED)
    text.normal("Trying to spend", "coins from another chain.", "Continue?")
    return await confirm(ctx, text, ButtonRequestType.SignTx)
