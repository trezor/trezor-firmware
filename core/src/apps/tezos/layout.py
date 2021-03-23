from trezor import ui
from trezor.enums import ButtonRequestType
from trezor.strings import format_amount
from trezor.ui.components.tt.scroll import Paginated
from trezor.ui.components.tt.text import Text
from trezor.utils import chunks

from apps.common.confirm import require_confirm, require_hold_to_confirm

from .helpers import TEZOS_AMOUNT_DECIMALS


async def require_confirm_tx(ctx, to, value):
    text = Text("Confirm sending", ui.ICON_SEND, ui.GREEN)
    text.bold(format_tezos_amount(value))
    text.normal("to")
    text.mono(*split_address(to))
    await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_fee(ctx, value, fee):
    text = Text("Confirm transaction", ui.ICON_SEND, ui.GREEN)
    text.normal("Amount:")
    text.bold(format_tezos_amount(value))
    text.normal("Fee:")
    text.bold(format_tezos_amount(fee))
    await require_hold_to_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_origination(ctx, address):
    text = Text("Confirm origination", ui.ICON_SEND, ui.ORANGE)
    text.normal("Address:")
    text.mono(*split_address(address))
    await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_origination_fee(ctx, balance, fee):
    text = Text("Confirm origination", ui.ICON_SEND, ui.ORANGE)
    text.normal("Balance:")
    text.bold(format_tezos_amount(balance))
    text.normal("Fee:")
    text.bold(format_tezos_amount(fee))
    await require_hold_to_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_delegation_baker(ctx, baker):
    text = Text("Confirm delegation", ui.ICON_SEND, ui.BLUE)
    text.normal("Baker address:")
    text.mono(*split_address(baker))
    await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_set_delegate(ctx, fee):
    text = Text("Confirm delegation", ui.ICON_SEND, ui.BLUE)
    text.normal("Fee:")
    text.bold(format_tezos_amount(fee))
    await require_hold_to_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_register_delegate(ctx, address, fee):
    text = Text("Register delegate", ui.ICON_SEND, ui.BLUE)
    text.bold("Fee: " + format_tezos_amount(fee))
    text.normal("Address:")
    text.mono(*split_address(address))
    await require_hold_to_confirm(ctx, text, ButtonRequestType.SignTx)


def split_address(address):
    return chunks(address, 18)


def split_proposal(proposal):
    return chunks(proposal, 17)


def format_tezos_amount(value):
    formatted_value = format_amount(value, TEZOS_AMOUNT_DECIMALS)
    return formatted_value + " XTZ"


async def require_confirm_ballot(ctx, proposal, ballot):
    text = Text("Submit ballot", ui.ICON_SEND, icon_color=ui.PURPLE)
    text.bold("Ballot: {}".format(ballot))
    text.bold("Proposal:")
    text.mono(*split_proposal(proposal))
    await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_proposals(ctx, proposals):
    if len(proposals) > 1:
        title = "Submit proposals"
    else:
        title = "Submit proposal"

    pages = []
    for page, proposal in enumerate(proposals):
        text = Text(title, ui.ICON_SEND, icon_color=ui.PURPLE)
        text.bold("Proposal {}: ".format(page + 1))
        text.mono(*split_proposal(proposal))
        pages.append(text)
    paginated = Paginated(pages)

    await require_confirm(ctx, paginated, ButtonRequestType.SignTx)


async def require_confirm_delegation_manager_withdraw(ctx, address):
    text = Text("Remove delegation", ui.ICON_RECEIVE, icon_color=ui.RED)
    text.bold("Delegator:")
    text.mono(*split_address(address))
    await require_confirm(ctx, text, ButtonRequestType.SignTx)


async def require_confirm_manager_remove_delegate(ctx, fee):
    text = Text("Remove delegation", ui.ICON_RECEIVE, ui.RED)
    text.normal("Fee:")
    text.bold(format_tezos_amount(fee))
    await require_hold_to_confirm(ctx, text, ButtonRequestType.SignTx)
