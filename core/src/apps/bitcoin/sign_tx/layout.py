from micropython import const
from ubinascii import hexlify

from trezor.enums import AmountUnit, ButtonRequestType, OutputScriptType
from trezor.strings import format_amount
from trezor.ui import layouts

from .. import addresses
from . import omni

if False:
    from trezor import wire
    from trezor.messages import TxOutput
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
    return "%s %s" % (format_amount(amount, decimals), shortcut)


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
            layout = layouts.confirm_hex(
                ctx,
                "op_return",
                title="OP_RETURN",
                data=hexlify(data).decode(),
                br_code=ButtonRequestType.ConfirmOutput,
            )
    else:
        assert output.address is not None
        address_short = addresses.address_short(coin, output.address)
        layout = layouts.confirm_output(
            ctx, address_short, format_coin_amount(output.amount, coin, amount_unit)
        )

    await layout


async def confirm_decred_sstx_submission(
    ctx: wire.Context, output: TxOutput, coin: CoinInfo, amount_unit: AmountUnit
) -> None:
    assert output.address is not None
    address_short = addresses.address_short(coin, output.address)

    await layouts.confirm_decred_sstx_submission(
        ctx, address_short, format_coin_amount(output.amount, coin, amount_unit)
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
    coin: CoinInfo,
    amount_unit: AmountUnit,
) -> None:
    await layouts.confirm_total(
        ctx,
        total_amount=format_coin_amount(spending, coin, amount_unit),
        fee_amount=format_coin_amount(fee, coin, amount_unit),
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
        text = "Locktime for this\ntransaction is set to\ntimestamp:\n{}"
        param = str(lock_time)

    await layouts.confirm_metadata(
        ctx,
        "nondefault_locktime",
        title,
        text,
        param,
        br_code=ButtonRequestType.SignTx,
    )
