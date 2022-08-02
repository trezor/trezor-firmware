from micropython import const
from typing import TYPE_CHECKING
from ubinascii import hexlify

from trezor import ui, utils, wire
from trezor.enums import AmountUnit, ButtonRequestType, OutputScriptType
from trezor.strings import format_amount, format_timestamp
from trezor.ui import layouts

from .. import addresses
from . import omni

if not utils.BITCOIN_ONLY:
    from trezor.ui.layouts import altcoin


if TYPE_CHECKING:
    from typing import Any

    from trezor.messages import TxAckPaymentRequest, TxOutput
    from trezor.ui.layouts import LayoutType

    from apps.common.coininfo import CoinInfo

_LOCKTIME_TIMESTAMP_MIN_VALUE = const(500_000_000)


def format_coin_amount(amount: int, coin: CoinInfo, amount_unit: AmountUnit) -> str:
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
    return f"{format_amount(amount, decimals)} {shortcut}"


async def confirm_output(
    ctx: wire.Context, output: TxOutput, coin: CoinInfo, amount_unit: AmountUnit
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
            layout = layouts.confirm_blob(
                ctx,
                "op_return",
                title="OP_RETURN",
                data=data,
                br_code=ButtonRequestType.ConfirmOutput,
            )
    else:
        assert output.address is not None
        address_short = addresses.address_short(coin, output.address)
        if output.payment_req_index is not None:
            title = "Confirm details"
            icon = ui.ICON_CONFIRM
        else:
            title = "Confirm sending"
            icon = ui.ICON_SEND

        layout = layouts.confirm_output(
            ctx,
            address_short,
            format_coin_amount(output.amount, coin, amount_unit),
            title=title,
            icon=icon,
        )

    await layout


async def confirm_decred_sstx_submission(
    ctx: wire.Context, output: TxOutput, coin: CoinInfo, amount_unit: AmountUnit
) -> None:
    assert output.address is not None
    address_short = addresses.address_short(coin, output.address)

    await altcoin.confirm_decred_sstx_submission(
        ctx, address_short, format_coin_amount(output.amount, coin, amount_unit)
    )


async def confirm_payment_request(
    ctx: wire.Context,
    msg: TxAckPaymentRequest,
    coin: CoinInfo,
    amount_unit: AmountUnit,
) -> Any:
    memo_texts = []
    for m in msg.memos:
        if m.text_memo is not None:
            memo_texts.append(m.text_memo.text)
        elif m.refund_memo is not None:
            pass
        elif m.coin_purchase_memo is not None:
            memo_texts.append(f"Buying {m.coin_purchase_memo.amount}.")
        else:
            raise wire.DataError("Unrecognized memo type in payment request memo.")

    assert msg.amount is not None

    return await layouts.confirm_payment_request(
        ctx,
        msg.recipient_name,
        format_coin_amount(msg.amount, coin, amount_unit),
        memo_texts,
    )


async def confirm_replacement(ctx: wire.Context, description: str, txid: bytes) -> None:
    await layouts.confirm_replacement(
        ctx,
        description,
        hexlify(txid).decode(),
    )


async def confirm_modify_output(
    ctx: wire.Context,
    txo: TxOutput,
    orig_txo: TxOutput,
    coin: CoinInfo,
    amount_unit: AmountUnit,
) -> None:
    assert txo.address is not None
    address_short = addresses.address_short(coin, txo.address)
    amount_change = txo.amount - orig_txo.amount
    await layouts.confirm_modify_output(
        ctx,
        address_short,
        amount_change,
        format_coin_amount(abs(amount_change), coin, amount_unit),
        format_coin_amount(txo.amount, coin, amount_unit),
    )


async def confirm_modify_fee(
    ctx: wire.Context,
    user_fee_change: int,
    total_fee_new: int,
    coin: CoinInfo,
    amount_unit: AmountUnit,
) -> None:
    await layouts.confirm_modify_fee(
        ctx,
        user_fee_change,
        format_coin_amount(abs(user_fee_change), coin, amount_unit),
        format_coin_amount(total_fee_new, coin, amount_unit),
    )


async def confirm_joint_total(
    ctx: wire.Context,
    spending: int,
    total: int,
    coin: CoinInfo,
    amount_unit: AmountUnit,
) -> None:
    await layouts.confirm_joint_total(
        ctx,
        spending_amount=format_coin_amount(spending, coin, amount_unit),
        total_amount=format_coin_amount(total, coin, amount_unit),
    )


async def confirm_total(
    ctx: wire.Context,
    spending: int,
    fee: int,
    fee_rate: float,
    coin: CoinInfo,
    amount_unit: AmountUnit,
) -> None:
    fee_rate_str: str | None = None

    if fee_rate >= 0:
        # Use format_amount to get correct thousands separator -- micropython's built-in
        # formatting doesn't add thousands sep to floating point numbers.
        # We multiply by 10 to get a fixed-point integer with one decimal place,
        # and add 0.5 to round to the nearest integer.
        fee_rate_formatted = format_amount(int(fee_rate * 10 + 0.5), 1)
        fee_rate_str = f"({fee_rate_formatted} sat/{'v' if coin.segwit else ''}B)"

    await layouts.confirm_total(
        ctx,
        total_amount=format_coin_amount(spending, coin, amount_unit),
        fee_amount=format_coin_amount(fee, coin, amount_unit),
        fee_rate_amount=fee_rate_str,
    )


async def confirm_feeoverthreshold(
    ctx: wire.Context, fee: int, coin: CoinInfo, amount_unit: AmountUnit
) -> None:
    fee_amount = format_coin_amount(fee, coin, amount_unit)
    await layouts.confirm_metadata(
        ctx,
        "fee_over_threshold",
        "High fee",
        "The fee of\n{}is unexpectedly high.",
        fee_amount,
        ButtonRequestType.FeeOverThreshold,
    )


async def confirm_change_count_over_threshold(
    ctx: wire.Context, change_count: int
) -> None:
    await layouts.confirm_metadata(
        ctx,
        "change_count_over_threshold",
        "Warning",
        "There are {}\nchange-outputs.\n",
        str(change_count),
        ButtonRequestType.SignTx,
    )


async def confirm_unverified_external_input(ctx: wire.Context) -> None:
    await layouts.confirm_metadata(
        ctx,
        "unverified_external_input",
        "Warning",
        "The transaction contains unverified external inputs.",
        br_code=ButtonRequestType.SignTx,
    )


async def confirm_nondefault_locktime(
    ctx: wire.Context, lock_time: int, lock_time_disabled: bool
) -> None:
    if lock_time_disabled:
        title = "Warning"
        text = "Locktime is set but will\nhave no effect.\n"
        param: str | None = None
    elif lock_time < _LOCKTIME_TIMESTAMP_MIN_VALUE:
        title = "Confirm locktime"
        text = "Locktime for this\ntransaction is set to\nblockheight:\n{}"
        param = str(lock_time)
    else:
        title = "Confirm locktime"
        text = "Locktime for this\ntransaction is set to:\n{}"
        param = format_timestamp(lock_time)

    await layouts.confirm_metadata(
        ctx,
        "nondefault_locktime",
        title,
        text,
        param,
        br_code=ButtonRequestType.SignTx,
    )
