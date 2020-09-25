from ubinascii import hexlify

from trezor.messages import OutputScriptType
from trezor.strings import format_amount

from apps.common.confirm import require_interact

from .. import addresses
from . import omni

if False:
    from trezor import wire
    from trezor.messages.TxOutput import TxOutput

    from apps.common.coininfo import CoinInfo


def format_coin_amount(amount: int, coin: CoinInfo) -> str:
    return "%s %s" % (format_amount(amount, coin.decimals), coin.coin_shortcut)


# XXX we might be able to inline everything into helpers.py confirm_dialog methods and get rid of this file
async def confirm_output(ctx: wire.Context, output: TxOutput, coin: CoinInfo) -> None:
    kwargs = {}
    if output.script_type == OutputScriptType.PAYTOOPRETURN:
        data = output.op_return_data
        assert data is not None
        if omni.is_valid(data):
            kwargs["output_omni_data"] = omni.parse(data)
        else:
            # generic OP_RETURN
            kwargs["output_op_return_data"] = hexlify(data).decode()
    else:
        address = output.address
        assert address is not None
        kwargs["output_amount"] = format_coin_amount(output.amount, coin)
        kwargs["output_address"] = addresses.address_short(coin, address)

    await require_interact(ctx, "confirm_output", **kwargs)


async def confirm_joint_total(
    ctx: wire.Context, spending: int, total: int, coin: CoinInfo
) -> None:
    await require_interact(
        ctx,
        "confirm_joint_total",
        spending_amount=format_coin_amount(spending, coin),
        total_amount=format_coin_amount(total, coin),
    )


async def confirm_total(
    ctx: wire.Context, spending: int, fee: int, coin: CoinInfo
) -> None:
    await require_interact(
        ctx,
        "confirm_total",
        total_amount=format_coin_amount(spending, coin),
        fee_amount=format_coin_amount(fee, coin),
    )


async def confirm_feeoverthreshold(ctx: wire.Context, fee: int, coin: CoinInfo) -> None:
    await require_interact(
        ctx, "confirm_feeoverthreshold", fee_amount=format_coin_amount(fee, coin)
    )


async def confirm_change_count_over_threshold(
    ctx: wire.Context, change_count: int
) -> None:
    await require_interact(
        ctx, "confirm_change_count_over_threshold", change_count=change_count
    )


async def confirm_nondefault_locktime(
    ctx: wire.Context, lock_time: int, lock_time_disabled: bool
) -> None:
    await require_interact(
        ctx,
        "confirm_nondefault_locktime",
        lock_time_disabled=str(lock_time_disabled),
        lock_time=str(lock_time),
    )
