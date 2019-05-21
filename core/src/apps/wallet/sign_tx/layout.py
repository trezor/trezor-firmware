from micropython import const
from ubinascii import hexlify

from trezor import ui
from trezor.messages import ButtonRequestType, OutputScriptType
from trezor.utils import chunks, format_amount

_LOCKTIME_TIMESTAMP_MIN_VALUE = const(500000000)


def format_coin_amount(amount, coin):
    return "%s %s" % (format_amount(amount, 8), coin.coin_shortcut)


def split_address(address):
    return chunks(address, 17)


def split_op_return(data):
    return chunks(data, 18)


async def confirm_output(ctx, output, coin):
    from trezor.ui.text import Text
    from apps.common.confirm import confirm
    from apps.wallet.sign_tx import addresses, omni

    if output.script_type == OutputScriptType.PAYTOOPRETURN:
        data = output.op_return_data
        if omni.is_valid(data):
            # OMNI transaction
            text = Text("OMNI transaction", ui.ICON_SEND, icon_color=ui.GREEN)
            text.normal(omni.parse(data))
        else:
            # generic OP_RETURN
            data = hexlify(data).decode()
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
    from trezor.ui.text import Text
    from apps.common.confirm import hold_to_confirm

    text = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    text.normal("Total amount:")
    text.bold(format_coin_amount(spending, coin))
    text.normal("including fee:")
    text.bold(format_coin_amount(fee, coin))
    return await hold_to_confirm(ctx, text, ButtonRequestType.SignTx)


async def confirm_feeoverthreshold(ctx, fee, coin):
    from trezor.ui.text import Text
    from apps.common.confirm import confirm

    text = Text("High fee", ui.ICON_SEND, ui.GREEN)
    text.normal("The fee of")
    text.bold(format_coin_amount(fee, coin))
    text.normal("is unexpectedly high.", "Continue?")
    return await confirm(ctx, text, ButtonRequestType.FeeOverThreshold)


async def confirm_foreign_address(ctx, address_n, coin):
    from trezor.ui.text import Text
    from apps.common.confirm import confirm

    text = Text("Confirm sending", ui.ICON_SEND, ui.RED)
    text.normal("Trying to spend", "coins from another chain.", "Continue?")
    return await confirm(ctx, text, ButtonRequestType.SignTx)


async def confirm_nondefault_locktime(ctx, lock_time):
    from trezor.ui.text import Text
    from apps.common.confirm import confirm

    text = Text("Confirm locktime", ui.ICON_SEND, ui.GREEN)
    text.normal("Locktime for this transaction is set to")
    if lock_time < _LOCKTIME_TIMESTAMP_MIN_VALUE:
        text.normal("blockheight:")
    else:
        text.normal("timestamp:")
    text.bold(str(lock_time))
    text.normal("Continue?")
    return await confirm(ctx, text, ButtonRequestType.SignTx)
