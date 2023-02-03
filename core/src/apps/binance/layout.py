from typing import TYPE_CHECKING, Sequence

from trezor.enums import ButtonRequestType
from trezor.strings import format_amount
from trezor.ui.layouts import confirm_properties

from .helpers import DECIMALS

if TYPE_CHECKING:
    from trezor.messages import (
        BinanceCancelMsg,
        BinanceInputOutput,
        BinanceOrderMsg,
        BinanceTransferMsg,
    )
    from trezor.wire import Context


async def require_confirm_transfer(ctx: Context, msg: BinanceTransferMsg) -> None:
    items: list[tuple[str, str, str]] = []

    def make_input_output_pages(msg: BinanceInputOutput, direction: str) -> None:
        for coin in msg.coins:
            items.append(
                (
                    direction,
                    format_amount(coin.amount, DECIMALS) + " " + coin.denom,
                    msg.address,
                )
            )

    for txinput in msg.inputs:
        make_input_output_pages(txinput, "Confirm input")

    for txoutput in msg.outputs:
        make_input_output_pages(txoutput, "Confirm output")

    await _confirm_transfer(ctx, items)


async def _confirm_transfer(
    ctx: Context, inputs_outputs: Sequence[tuple[str, str, str]]
) -> None:
    from trezor.ui.layouts import confirm_output

    for index, (title, amount, address) in enumerate(inputs_outputs):
        # Having hold=True on the last item
        hold = index == len(inputs_outputs) - 1
        await confirm_output(
            ctx,
            address,
            amount,
            title,
            hold=hold,
        )


async def require_confirm_cancel(ctx: Context, msg: BinanceCancelMsg) -> None:
    await confirm_properties(
        ctx,
        "confirm_cancel",
        "Confirm cancel",
        (
            ("Sender address:", str(msg.sender)),
            ("Pair:", str(msg.symbol)),
            ("Order ID:", str(msg.refid)),
        ),
        hold=True,
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_order(ctx: Context, msg: BinanceOrderMsg) -> None:
    from trezor.enums import BinanceOrderSide

    if msg.side == BinanceOrderSide.BUY:
        side = "Buy"
    elif msg.side == BinanceOrderSide.SELL:
        side = "Sell"
    else:
        side = "Unknown"

    await confirm_properties(
        ctx,
        "confirm_order",
        "Confirm order",
        (
            ("Sender address:", str(msg.sender)),
            ("Pair:", str(msg.symbol)),
            ("Side:", side),
            ("Quantity:", format_amount(msg.quantity, DECIMALS)),
            ("Price:", format_amount(msg.price, DECIMALS)),
        ),
        hold=True,
        br_code=ButtonRequestType.SignTx,
    )
