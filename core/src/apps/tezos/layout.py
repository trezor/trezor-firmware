from micropython import const

from trezor import ui, wire
from trezor.messages import ButtonRequestType, MessageType
from trezor.messages.ButtonRequest import ButtonRequest
from trezor.ui.confirm import CANCELLED, ConfirmDialog
from trezor.ui.scroll import Scrollpage, animate_swipe, paginate
from trezor.ui.text import Text
from trezor.utils import chunks, format_amount

from apps.common.confirm import require_confirm, require_hold_to_confirm
from apps.tezos.helpers import TEZOS_AMOUNT_DIVISIBILITY


async def require_confirm_tx(ctx, to, value):
    text = Text("Confirm sending", ui.ICON_SEND, icon_color=ui.GREEN)
    text.bold(format_tezos_amount(value))
    text.normal("to")
    text.mono(*split_address(to))
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_fee(ctx, value, fee):
    text = Text("Confirm transaction", ui.ICON_SEND, icon_color=ui.GREEN)
    text.normal("Amount:")
    text.bold(format_tezos_amount(value))
    text.normal("Fee:")
    text.bold(format_tezos_amount(fee))
    await require_hold_to_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_origination(ctx, address):
    text = Text("Confirm origination", ui.ICON_SEND, icon_color=ui.ORANGE)
    text.normal("Address:")
    text.mono(*split_address(address))
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_origination_fee(ctx, balance, fee):
    text = Text("Confirm origination", ui.ICON_SEND, icon_color=ui.ORANGE)
    text.normal("Balance:")
    text.bold(format_tezos_amount(balance))
    text.normal("Fee:")
    text.bold(format_tezos_amount(fee))
    await require_hold_to_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_delegation_baker(ctx, baker):
    text = Text("Confirm delegation", ui.ICON_SEND, icon_color=ui.BLUE)
    text.normal("Baker address:")
    text.mono(*split_address(baker))
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_set_delegate(ctx, fee):
    text = Text("Confirm delegation", ui.ICON_SEND, icon_color=ui.BLUE)
    text.normal("Fee:")
    text.bold(format_tezos_amount(fee))
    await require_hold_to_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_register_delegate(ctx, address, fee):
    text = Text("Register delegate", ui.ICON_SEND, icon_color=ui.BLUE)
    text.bold("Fee: " + format_tezos_amount(fee))
    text.normal("Address:")
    text.mono(*split_address(address))
    await require_hold_to_confirm(ctx, text, ButtonRequestType.SignTx)


def split_address(address):
    return chunks(address, 18)


def split_proposal(proposal):
    return chunks(proposal, 17)


def format_tezos_amount(value):
    formatted_value = format_amount(value, TEZOS_AMOUNT_DIVISIBILITY)
    return formatted_value + " XTZ"


async def require_confirm_ballot(ctx, proposal, ballot):
    text = Text("Submit ballot", ui.ICON_SEND, icon_color=ui.PURPLE)
    text.bold("Ballot: {}".format(ballot))
    text.bold("Proposal:")
    text.mono(*split_proposal(proposal))
    await require_confirm(ctx, text, ButtonRequestType.SignTx)


# use, when there are more then one proposals in one operation
async def require_confirm_proposals(ctx, proposals):
    await ctx.call(ButtonRequest(code=ButtonRequestType.SignTx), MessageType.ButtonAck)
    first_page = const(0)
    pages = proposals
    title = "Submit proposals" if len(proposals) > 1 else "Submit proposal"

    paginator = paginate(show_proposal_page, len(pages), first_page, pages, title)
    return await ctx.wait(paginator)


@ui.layout
async def show_proposal_page(page: int, page_count: int, pages: list, title: str):
    text = Text(title, ui.ICON_SEND, icon_color=ui.PURPLE)
    text.bold("Proposal {}: ".format(page + 1))
    text.mono(*split_proposal(pages[page]))
    content = Scrollpage(text, page, page_count)

    if page + 1 >= page_count:
        confirm = await ConfirmDialog(content)
        if confirm == CANCELLED:
            raise wire.ActionCancelled("Cancelled")
    else:
        content.render()
        await animate_swipe()
