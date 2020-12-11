from trezor import ui
from trezor.messages import (
    BinanceCancelMsg,
    BinanceInputOutput,
    BinanceOrderMsg,
    BinanceOrderSide,
    BinanceTransferMsg,
    ButtonRequestType,
)
from trezor.strings import format_amount
from trezor.ui.components.tt.scroll import Paginated
from trezor.ui.components.tt.text import Text

from apps.common.confirm import require_hold_to_confirm
from apps.common.layout import split_address

from . import helpers


async def require_confirm_transfer(ctx, msg: BinanceTransferMsg):
    def make_input_output_pages(msg: BinanceInputOutput, direction):
        pages = []
        for coin in msg.coins:
            coin_page = Text("Confirm " + direction, ui.ICON_SEND, icon_color=ui.GREEN)
            coin_page.bold(
                format_amount(coin.amount, helpers.DECIMALS) + " " + coin.denom
            )
            coin_page.normal("to")
            coin_page.mono(*split_address(msg.address))
            pages.append(coin_page)

        return pages

    pages = []
    for txinput in msg.inputs:
        pages.extend(make_input_output_pages(txinput, "input"))

    for txoutput in msg.outputs:
        pages.extend(make_input_output_pages(txoutput, "output"))

    return await require_hold_to_confirm(
        ctx, Paginated(pages), ButtonRequestType.ConfirmOutput
    )


async def require_confirm_cancel(ctx, msg: BinanceCancelMsg):
    page1 = Text("Confirm cancel 1/2", ui.ICON_SEND, icon_color=ui.GREEN)
    page1.normal("Sender address:")
    page1.bold(msg.sender)
    page1.normal("Pair:")
    page1.bold(msg.symbol)

    page2 = Text("Confirm cancel 2/2", ui.ICON_SEND, icon_color=ui.GREEN)
    page2.normal("Order ID:")
    page2.bold(msg.refid)

    return await require_hold_to_confirm(
        ctx, Paginated([page1, page2]), ButtonRequestType.SignTx
    )


async def require_confirm_order(ctx, msg: BinanceOrderMsg):
    page1 = Text("Confirm order 1/3", ui.ICON_SEND, icon_color=ui.GREEN)
    page1.normal("Sender address:")
    page1.bold(msg.sender)

    page2 = Text("Confirm order 2/3", ui.ICON_SEND, icon_color=ui.GREEN)
    page2.normal("Pair:")
    page2.bold(msg.symbol)
    page2.normal("Side:")
    if msg.side == BinanceOrderSide.BUY:
        page2.bold("Buy")
    elif msg.side == BinanceOrderSide.SELL:
        page2.bold("Sell")

    page3 = Text("Confirm order 3/3", ui.ICON_SEND, icon_color=ui.GREEN)
    page3.normal("Quantity:")
    page3.bold(format_amount(msg.quantity, helpers.DECIMALS))
    page3.normal("Price:")
    page3.bold(format_amount(msg.price, helpers.DECIMALS))

    return await require_hold_to_confirm(
        ctx, Paginated([page1, page2, page3]), ButtonRequestType.SignTx
    )
