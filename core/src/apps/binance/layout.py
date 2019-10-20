from trezor import ui
from trezor.messages import (
    BinanceCancelMsg,
    BinanceInputOutput,
    BinanceOrderMsg,
    BinanceOrderSide,
    BinanceTransferMsg,
    ButtonRequestType,
)
from trezor.ui.scroll import Paginated
from trezor.ui.text import Text
from trezor.utils import format_amount

from . import helpers

from apps.common.confirm import hold_to_confirm
from apps.common.layout import split_address


async def require_confirm_transfer(ctx, msg: BinanceTransferMsg):
    def make_input_output_pages(msg: BinanceInputOutput, direction):
        pages = []
        for coin in msg.coins:
            coin_page = Text("Confirm " + direction, ui.ICON_SEND, icon_color=ui.GREEN)
            coin_page.bold(
                format_amount(coin.amount, helpers.DIVISIBILITY) + " " + coin.denom
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

    return await hold_to_confirm(ctx, Paginated(pages), ButtonRequestType.ConfirmOutput)


async def require_confirm_cancel(ctx, msg: BinanceCancelMsg):
    text = Text("Confirm cancel", ui.ICON_SEND, icon_color=ui.GREEN)
    text.normal("Reference id:")
    text.bold(msg.refid)
    return await hold_to_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_order(ctx, msg: BinanceOrderMsg):
    page1 = Text("Confirm order", ui.ICON_SEND, icon_color=ui.GREEN)
    page1.normal("Sender address:")
    page1.bold(msg.sender)

    page2 = Text("Confirm order", ui.ICON_SEND, icon_color=ui.GREEN)
    page2.normal("side:")
    if msg.side == BinanceOrderSide.BUY:
        page2.bold("buy")
    elif msg.side == BinanceOrderSide.SELL:
        page2.bold("sell")

    page3 = Text("Confirm order", ui.ICON_SEND, icon_color=ui.GREEN)
    page3.normal("Quantity:")
    page3.bold(str(msg.quantity))
    page3.normal("Price:")
    page3.bold(str(msg.price))

    return await hold_to_confirm(
        ctx, Paginated([page1, page2, page3]), ButtonRequestType.SignTx
    )
