from trezor import wire
from trezor.enums import BinanceOrderSide, ButtonRequestType
from trezor.messages import (
    BinanceCancelMsg,
    BinanceInputOutput,
    BinanceOrderMsg,
    BinanceTransferMsg,
)
from trezor.strings import format_amount
from trezor.ui.layouts import confirm_properties
from trezor.ui.layouts.tt.altcoin import confirm_transfer_binance

from . import helpers


async def require_confirm_transfer(ctx: wire.Context, msg: BinanceTransferMsg) -> None:
    items = []

    def make_input_output_pages(msg: BinanceInputOutput, direction: str) -> None:
        for coin in msg.coins:
            items.append(
                (
                    direction,
                    format_amount(coin.amount, helpers.DECIMALS) + " " + coin.denom,
                    msg.address,
                )
            )

    for txinput in msg.inputs:
        make_input_output_pages(txinput, "Confirm input")

    for txoutput in msg.outputs:
        make_input_output_pages(txoutput, "Confirm output")

    await confirm_transfer_binance(ctx, items)


async def require_confirm_cancel(ctx: wire.Context, msg: BinanceCancelMsg) -> None:
    await confirm_properties(
        ctx,
        "confirm_cancel",
        title="Confirm cancel",
        props=[
            ("Sender address:", msg.sender),
            ("Pair:", msg.symbol),
            ("Order ID:", msg.refid),
        ],
        hold=True,
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_order(ctx: wire.Context, msg: BinanceOrderMsg) -> None:
    # TODO: could set required in protobuf
    assert msg.quantity is not None
    assert msg.price is not None
    if msg.side == BinanceOrderSide.BUY:
        side = "Buy"
    elif msg.side == BinanceOrderSide.SELL:
        side = "Sell"
    else:
        side = "?"

    await confirm_properties(
        ctx,
        "confirm_order",
        title="Confirm order",
        props=[
            ("Sender address:", msg.sender),
            ("Pair:", msg.symbol),
            ("Side:", side),
            ("Quantity:", format_amount(msg.quantity, helpers.DECIMALS)),
            ("Price:", format_amount(msg.price, helpers.DECIMALS)),
        ],
        hold=True,
        br_code=ButtonRequestType.SignTx,
    )
