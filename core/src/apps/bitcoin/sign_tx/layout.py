from micropython import const
from ubinascii import hexlify

from trezor.messages import AmountUnit, ButtonRequestType, MemoType, OutputScriptType
from trezor.strings import format_amount
from trezor.ui import layouts
from trezor.ui.components.common.confirm import CONFIRMED, INFO
from trezor.ui.layouts import require

from apps.common import coininfo

from .. import addresses
from . import omni

if False:
    from typing import Optional

    from trezor import wire
    from trezor.messages.SignTx import EnumTypeAmountUnit
    from trezor.messages.TxOutput import TxOutput
    from trezor.messages.TxAckPaymentRequest import TxAckPaymentRequest
    from trezor.ui.layouts import LayoutType

    from apps.common.coininfo import CoinInfo

_LOCKTIME_TIMESTAMP_MIN_VALUE = const(500_000_000)


def format_coin_amount(
    amount: int, coin: CoinInfo, amount_unit: EnumTypeAmountUnit
) -> str:
    decimals, shortcut = coin.decimals, coin.coin_shortcut
    if amount_unit == AmountUnit.SATOSHI:
        decimals = 0
        shortcut = "sat " + shortcut
    elif amount_unit == AmountUnit.MICROBITCOIN and decimals >= 6:
        decimals -= 6
        shortcut = "u" + shortcut
    elif amount_unit == AmountUnit.MILLIBITCOIN and decimals >= 3:
        decimals -= 3
        shortcut = "m" + shortcut
    # we don't need to do anything for AmountUnit.BITCOIN
    return "%s %s" % (format_amount(amount, decimals), shortcut)


async def confirm_output(
    ctx: wire.Context, output: TxOutput, coin: CoinInfo, amount_unit: EnumTypeAmountUnit
) -> None:
    if output.script_type == OutputScriptType.PAYTOOPRETURN:
        data = output.op_return_data
        assert data is not None
        if omni.is_valid(data):
            # OMNI transaction
            layout: LayoutType = layouts.confirm_metadata(
                ctx,
                "omni_transaction",
                "OMNI transaction",
                omni.parse(data),
                br_code=ButtonRequestType.ConfirmOutput,
            )
        else:
            # generic OP_RETURN
            layout = layouts.confirm_hex(
                ctx,
                "op_return",
                "OP_RETURN",
                hexlify(data).decode(),
                ButtonRequestType.ConfirmOutput,
            )
    else:
        assert output.address is not None
        address_short = addresses.address_short(coin, output.address)
        layout = layouts.confirm_output(
            ctx,
            address_short,
            format_coin_amount(output.amount, coin, amount_unit),
            output.payment_req_index is not None,
        )

    await require(layout)


async def confirm_payment_request(
    ctx: wire.Context,
    msg: TxAckPaymentRequest,
    amount_unit: EnumTypeAmountUnit,
    coin: CoinInfo,
) -> bool:
    memo_texts = []
    for memo in msg.memos:
        if memo.type == MemoType.UTF8_TEXT:
            memo_texts.append(memo.data.decode())
        elif memo.type == MemoType.COIN_PURCHASE:
            assert memo.amount is not None  # checked by sanitizer
            assert memo.coin_name is not None  # checked by sanitizer
            memo_coin = coininfo.by_name(memo.coin_name)
            memo_texts.append(
                "Buying "
                + format_coin_amount(memo.amount, memo_coin, amount_unit)
                + "."
            )

    layout = layouts.confirm_payment_request(
        ctx,
        msg.recipient_name,
        format_coin_amount(msg.amount, coin, amount_unit),
        memo_texts,
    )

    result = await layout

    if result is INFO:
        return True  # show details

    if result is CONFIRMED:
        return False  # don't show details

    raise wire.ActionCancelled


async def confirm_replacement(ctx: wire.Context, description: str, txid: bytes) -> None:
    await require(
        layouts.confirm_replacement(
            ctx,
            description,
            hexlify(txid).decode(),
        )
    )


async def confirm_modify_fee(
    ctx: wire.Context,
    user_fee_change: int,
    total_fee_new: int,
    coin: CoinInfo,
    amount_unit: EnumTypeAmountUnit,
) -> None:
    await require(
        layouts.confirm_modify_fee(
            ctx,
            user_fee_change,
            format_coin_amount(abs(user_fee_change), coin, amount_unit),
            format_coin_amount(total_fee_new, coin, amount_unit),
        )
    )


async def confirm_joint_total(
    ctx: wire.Context,
    spending: int,
    total: int,
    coin: CoinInfo,
    amount_unit: EnumTypeAmountUnit,
) -> None:
    await require(
        layouts.confirm_joint_total(
            ctx,
            spending_amount=format_coin_amount(spending, coin, amount_unit),
            total_amount=format_coin_amount(total, coin, amount_unit),
        ),
    )


async def confirm_total(
    ctx: wire.Context,
    spending: int,
    fee: int,
    coin: CoinInfo,
    amount_unit: EnumTypeAmountUnit,
) -> None:
    await require(
        layouts.confirm_total(
            ctx,
            total_amount=format_coin_amount(spending, coin, amount_unit),
            fee_amount=format_coin_amount(fee, coin, amount_unit),
        ),
    )


async def confirm_feeoverthreshold(
    ctx: wire.Context, fee: int, coin: CoinInfo, amount_unit: EnumTypeAmountUnit
) -> None:
    fee_amount = format_coin_amount(fee, coin, amount_unit)
    await require(
        layouts.confirm_metadata(
            ctx,
            "fee_over_threshold",
            "High fee",
            "The fee of\n{}is unexpectedly high.",
            fee_amount,
            ButtonRequestType.FeeOverThreshold,
        )
    )


async def confirm_change_count_over_threshold(
    ctx: wire.Context, change_count: int
) -> None:
    await require(
        layouts.confirm_metadata(
            ctx,
            "change_count_over_threshold",
            "Warning",
            "There are {}\nchange-outputs.\n",
            str(change_count),
            ButtonRequestType.SignTx,
        )
    )


async def confirm_nondefault_locktime(
    ctx: wire.Context, lock_time: int, lock_time_disabled: bool
) -> None:
    if lock_time_disabled:
        title = "Warning"
        text = "Locktime is set but will\nhave no effect.\n"
        param: Optional[str] = None
    elif lock_time < _LOCKTIME_TIMESTAMP_MIN_VALUE:
        title = "Confirm locktime"
        text = "Locktime for this\ntransaction is set to\nblockheight:\n{}"
        param = str(lock_time)
    else:
        title = "Confirm locktime"
        text = "Locktime for this\ntransaction is set to\ntimestamp:\n{}"
        param = str(lock_time)

    await require(
        layouts.confirm_metadata(
            ctx,
            "nondefault_locktime",
            title,
            text,
            param,
            br_code=ButtonRequestType.SignTx,
        )
    )
