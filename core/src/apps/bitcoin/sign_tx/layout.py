from micropython import const
from ubinascii import hexlify

from trezor import ui
from trezor.messages import ButtonRequestType, OutputScriptType
from trezor.messages.TxOutputType import TxOutputType
from trezor.strings import format_amount
from trezor.utils import chunks

from apps.common import coininfo

if False:
    from typing import Iterator
    from trezor import wire

_LOCKTIME_TIMESTAMP_MIN_VALUE = const(500000000)


def format_coin_amount(amount: int, coin: coininfo.CoinInfo) -> str:
    return "%s %s" % (format_amount(amount, coin.decimals), coin.coin_shortcut)


def split_address(address: str) -> Iterator[str]:
    return chunks(address, 17)


def split_op_return(data: str) -> Iterator[str]:
    return chunks(data, 18)


async def confirm_output(
    ctx: wire.Context, output: TxOutputType, coin: coininfo.CoinInfo
) -> None:
    from trezor.ui.text import Text
    from apps.common.confirm import require_confirm
    from . import omni
    from .. import addresses

    if output.script_type == OutputScriptType.PAYTOOPRETURN:
        data = output.op_return_data
        if omni.is_valid(data):
            # OMNI transaction
            text = Text("OMNI transaction", ui.ICON_SEND, ui.GREEN)
            text.normal(omni.parse(data))
        else:
            # generic OP_RETURN
            hex_data = hexlify(data).decode()
            if len(hex_data) >= 18 * 5:
                hex_data = hex_data[: (18 * 5 - 3)] + "..."
            text = Text("OP_RETURN", ui.ICON_SEND, ui.GREEN)
            text.mono(*split_op_return(hex_data))
    else:
        address = output.address
        address_short = addresses.address_short(coin, address)
        text = Text("Confirm sending", ui.ICON_SEND, ui.GREEN)
        text.normal(format_coin_amount(output.amount, coin) + " to")
        text.mono(*split_address(address_short))
    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)


async def confirm_total(
    ctx: wire.Context, spending: int, fee: int, coin: coininfo.CoinInfo
) -> None:
    from trezor.ui.text import Text
    from apps.common.confirm import require_hold_to_confirm

    text = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    text.normal("Total amount:")
    text.bold(format_coin_amount(spending, coin))
    text.normal("including fee:")
    text.bold(format_coin_amount(fee, coin))
    await require_hold_to_confirm(ctx, text, ButtonRequestType.SignTx)


async def confirm_feeoverthreshold(
    ctx: wire.Context, fee: int, coin: coininfo.CoinInfo
) -> None:
    from trezor.ui.text import Text
    from apps.common.confirm import require_confirm

    text = Text("High fee", ui.ICON_SEND, ui.GREEN)
    text.normal("The fee of")
    text.bold(format_coin_amount(fee, coin))
    text.normal("is unexpectedly high.", "Continue?")
    await require_confirm(ctx, text, ButtonRequestType.FeeOverThreshold)


async def confirm_nondefault_locktime(ctx: wire.Context, lock_time: int) -> None:
    from trezor.ui.text import Text
    from apps.common.confirm import require_confirm

    text = Text("Confirm locktime", ui.ICON_SEND, ui.GREEN)
    text.normal("Locktime for this transaction is set to")
    if lock_time < _LOCKTIME_TIMESTAMP_MIN_VALUE:
        text.normal("blockheight:")
    else:
        text.normal("timestamp:")
    text.bold(str(lock_time))
    text.normal("Continue?")
    await require_confirm(ctx, text, ButtonRequestType.SignTx)
