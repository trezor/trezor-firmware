from micropython import const
from ubinascii import hexlify

from trezor.messages import OutputScriptType
from trezor.strings import format_amount
from trezor.ui import widgets
from trezor.ui.widgets import require

from .. import addresses
from . import omni

if False:
    from trezor import wire
    from trezor.messages.TxOutput import TxOutput

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
            title = "OMNI transaction"
            await require(widgets.confirm_output(ctx, title, data=omni.parse(data)))
        else:
            # generic OP_RETURN
            hex_data = hexlify(data).decode()
            await require(widgets.confirm_output(ctx, "OP_RETURN", hex_data=hex_data))
    else:
        address = output.address
        assert address is not None
        address_short = addresses.address_short(coin, address)
        await require(
            widgets.confirm_output(
                ctx,
                "Confirm sending",
                address=address_short,
                amount=format_coin_amount(output.amount, coin),
            )
        )


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
    await require(
        widgets.confirm_joint_total(
            ctx,
            spending_amount=format_coin_amount(spending, coin),
            total_amount=format_coin_amount(total, coin),
        ),
    )


async def confirm_total(
    ctx: wire.Context, spending: int, fee: int, coin: CoinInfo
) -> None:
    await require(
        widgets.confirm_total(
            ctx,
            total_amount=format_coin_amount(spending, coin),
            fee_amount=format_coin_amount(fee, coin),
        ),
    )


async def confirm_feeoverthreshold(ctx: wire.Context, fee: int, coin: CoinInfo) -> None:
    await require(
        widgets.confirm_feeoverthreshold(ctx, fee_amount=format_coin_amount(fee, coin))
    )


async def confirm_change_count_over_threshold(
    ctx: wire.Context, change_count: int
) -> None:
    await require(
        widgets.confirm_change_count_over_threshold(ctx, change_count=change_count)
    )


async def confirm_nondefault_locktime(
    ctx: wire.Context, lock_time: int, lock_time_disabled: bool
) -> None:
    if int(lock_time) < _LOCKTIME_TIMESTAMP_MIN_VALUE:
        await require(
            widgets.confirm_nondefault_locktime(
                ctx,
                lock_time_disabled=lock_time_disabled,
                lock_time_height=lock_time,
            ),
        )
    else:
        await require(
            widgets.confirm_nondefault_locktime(
                ctx,
                lock_time_disabled=lock_time_disabled,
                lock_time_stamp=lock_time,
            ),
        )
