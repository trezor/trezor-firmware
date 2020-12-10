from micropython import const
from ubinascii import hexlify

from trezor.messages import ButtonRequestType, OutputScriptType
from trezor.strings import format_amount
from trezor.ui import layouts
from trezor.ui.layouts import require

from .. import addresses
from . import omni

if False:
    from typing import Awaitable, Optional

    from trezor import wire
    from trezor.messages.TxOutput import TxOutput
    from trezor.ui.layouts import LayoutType

    from apps.common.coininfo import CoinInfo

_LOCKTIME_TIMESTAMP_MIN_VALUE = const(500_000_000)


def format_coin_amount(amount: int, coin: CoinInfo) -> str:
    return "%s %s" % (format_amount(amount, coin.decimals), coin.coin_shortcut)


async def confirm_output(ctx: wire.Context, output: TxOutput, coin: CoinInfo) -> None:
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
                ctx, "op_return", "OP_RETURN", data, ButtonRequestType.ConfirmOutput
            )
    else:
        assert output.address is not None
        address_short = addresses.address_short(coin, output.address)
        layout = layouts.confirm_output(
            ctx, address_short, format_coin_amount(output.amount, coin)
        )

    await require(layout)


async def confirm_replacement(ctx: wire.Context, description: str, txid: bytes) -> None:
    await require(
        layouts.confirm_replacement(
            ctx,
            description,
            hexlify(txid).decode(),
        )
    )


async def confirm_modify_fee(
    ctx: wire.Context, user_fee_change: int, total_fee_new: int, coin: CoinInfo
) -> None:
    await require(
        layouts.confirm_modify_fee(
            ctx,
            user_fee_change,
            format_coin_amount(abs(user_fee_change), coin),
            format_coin_amount(total_fee_new, coin),
        )
    )


async def confirm_joint_total(
    ctx: wire.Context, spending: int, total: int, coin: CoinInfo
) -> None:
    await require(
        layouts.confirm_joint_total(
            ctx,
            spending_amount=format_coin_amount(spending, coin),
            total_amount=format_coin_amount(total, coin),
        ),
    )


async def confirm_total(
    ctx: wire.Context, spending: int, fee: int, coin: CoinInfo
) -> None:
    await require(
        layouts.confirm_total(
            ctx,
            total_amount=format_coin_amount(spending, coin),
            fee_amount=format_coin_amount(fee, coin),
        ),
    )


async def confirm_feeoverthreshold(ctx: wire.Context, fee: int, coin: CoinInfo) -> None:
    fee_amount = format_coin_amount(fee, coin)
    await require(
        layouts.confirm_metadata(
            ctx,
            "fee_over_threshold",
            "High fee",
            "The fee of {} is unexpectedly high.",
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
            "There are {} change-outputs.",
            str(change_count),
            ButtonRequestType.SignTx,
        )
    )


async def confirm_nondefault_locktime(
    ctx: wire.Context, lock_time: int, lock_time_disabled: bool
) -> None:
    if lock_time_disabled:
        title = "Warning"
        text = "Locktime is set but will\nhave no effect."
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
