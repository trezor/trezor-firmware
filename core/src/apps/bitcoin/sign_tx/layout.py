from micropython import const
from ubinascii import hexlify

from trezor import ui
from trezor.messages import ButtonRequestType, OutputScriptType
from trezor.strings import format_amount
from trezor.ui.text import Text
from trezor.utils import chunks

from apps.common.confirm import require_confirm, require_hold_to_confirm

from .. import addresses
from . import omni

if False:
    from typing import Iterator
    from trezor import wire
    from trezor.messages.TxOutput import TxOutput

    from apps.common.coininfo import CoinInfo

_LOCKTIME_TIMESTAMP_MIN_VALUE = const(500_000_000)


def format_coin_amount(amount: int, coin: CoinInfo) -> str:
    return "%s %s" % (format_amount(amount, coin.decimals), coin.coin_shortcut)


def split_address(address: str) -> Iterator[str]:
    return chunks(address, 17)


def split_op_return(data: str) -> Iterator[str]:
    return chunks(data, 18)


async def confirm_output(ctx: wire.Context, output: TxOutput, coin: CoinInfo) -> None:
    if output.script_type == OutputScriptType.PAYTOOPRETURN:
        data = output.op_return_data
        assert data is not None
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
        assert address is not None
        address_short = addresses.address_short(coin, address)
        text = Text("Confirm sending", ui.ICON_SEND, ui.GREEN)
        text.normal(format_coin_amount(output.amount, coin) + " to")
        text.mono(*split_address(address_short))
    await require_confirm(ctx, text, ButtonRequestType.ConfirmOutput)


async def confirm_replacement(ctx: wire.Context, description: str, txid: bytes) -> None:
    text = Text(description, ui.ICON_SEND, ui.GREEN)
    text.normal("Confirm transaction ID:")
    hex_data = hexlify(txid).decode()
    if len(hex_data) >= 18 * 4:
        hex_data = hex_data[: (18 * 4 - 3)] + "..."
    text.mono(*split_op_return(hex_data))
    await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def confirm_modify_fee(
    ctx: wire.Context, user_fee_change: int, total_fee_new: int, coin: CoinInfo
) -> None:
    text = Text("Fee modification", ui.ICON_SEND, ui.GREEN)
    if user_fee_change == 0:
        text.normal("Your fee did not change.")
    else:
        if user_fee_change < 0:
            text.normal("Decrease your fee by:")
        else:
            text.normal("Increase your fee by:")
        text.bold(format_coin_amount(abs(user_fee_change), coin))
    text.br_half()
    text.normal("Transaction fee:")
    text.bold(format_coin_amount(total_fee_new, coin))
    await require_hold_to_confirm(ctx, text, ButtonRequestType.SignTx)


async def confirm_joint_total(
    ctx: wire.Context, spending: int, total: int, coin: CoinInfo
) -> None:
    text = Text("Joint transaction", ui.ICON_SEND, ui.GREEN)
    text.normal("You are contributing:")
    text.bold(format_coin_amount(spending, coin))
    text.normal("to the total amount:")
    text.bold(format_coin_amount(total, coin))
    await require_hold_to_confirm(ctx, text, ButtonRequestType.SignTx)


async def confirm_total(
    ctx: wire.Context, spending: int, fee: int, coin: CoinInfo
) -> None:
    text = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    text.normal("Total amount:")
    text.bold(format_coin_amount(spending, coin))
    text.normal("including fee:")
    text.bold(format_coin_amount(fee, coin))
    await require_hold_to_confirm(ctx, text, ButtonRequestType.SignTx)


async def confirm_feeoverthreshold(ctx: wire.Context, fee: int, coin: CoinInfo) -> None:
    text = Text("High fee", ui.ICON_SEND, ui.GREEN)
    text.normal("The fee of")
    text.bold(format_coin_amount(fee, coin))
    text.normal("is unexpectedly high.", "Continue?")
    await require_confirm(ctx, text, ButtonRequestType.FeeOverThreshold)


async def confirm_change_count_over_threshold(
    ctx: wire.Context, change_count: int
) -> None:
    text = Text("Warning", ui.ICON_SEND, ui.GREEN)
    text.normal("There are {}".format(change_count))
    text.normal("change-outputs.")
    text.br_half()
    text.normal("Continue?")
    await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def confirm_nondefault_locktime(
    ctx: wire.Context, lock_time: int, lock_time_disabled: bool
) -> None:
    if lock_time_disabled:
        text = Text("Warning", ui.ICON_SEND, ui.GREEN)
        text.normal("Locktime is set but will", "have no effect.")
        text.br_half()
    else:
        text = Text("Confirm locktime", ui.ICON_SEND, ui.GREEN)
        text.normal("Locktime for this", "transaction is set to")
        if lock_time < _LOCKTIME_TIMESTAMP_MIN_VALUE:
            text.normal("blockheight:")
        else:
            text.normal("timestamp:")
        text.bold(str(lock_time))

    text.normal("Continue?")
    await require_confirm(ctx, text, ButtonRequestType.SignTx)
