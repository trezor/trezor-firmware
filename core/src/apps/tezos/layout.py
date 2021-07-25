from trezor import ui
from trezor.enums import ButtonRequestType
from trezor.strings import format_amount
from trezor.ui.layouts import (
    confirm_hex,
    confirm_metadata,
    confirm_output,
    confirm_proposals_tezos,
    confirm_total,
)

from .helpers import TEZOS_AMOUNT_DECIMALS


async def require_confirm_tx(ctx, to, value):
    await confirm_output(
        ctx,
        to,
        format_tezos_amount(value),
        font_amount=ui.BOLD,
        to_str="\nto\n",
        width=18,
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_fee(ctx, value, fee):
    await confirm_total(
        ctx,
        total_amount=format_tezos_amount(value),
        total_label="Amount:\n",
        fee_amount=format_tezos_amount(fee),
        fee_label="\nFee:\n",
    )


async def require_confirm_origination(ctx, address):
    await confirm_hex(
        ctx,
        "confirm_origination",
        title="Confirm origination",
        description="Address:",
        data=address,
        width=18,
        truncate=True,
        icon_color=ui.ORANGE,
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_origination_fee(ctx, balance, fee):
    await confirm_total(
        ctx,
        title="Confirm origination",
        total_amount=format_tezos_amount(balance),
        total_label="Balance:\n",
        fee_amount=format_tezos_amount(fee),
        fee_label="\nFee:\n",
        icon_color=ui.ORANGE,
        br_type="confirm_origination_final",
    )


async def require_confirm_delegation_baker(ctx, baker):
    await confirm_hex(
        ctx,
        "confirm_delegation",
        title="Confirm delegation",
        description="Baker address:",
        data=baker,
        width=18,
        truncate=True,
        icon_color=ui.BLUE,
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_set_delegate(ctx, fee):
    await confirm_metadata(
        ctx,
        "confirm_delegation_final",
        title="Confirm delegation",
        content="Fee:\n{}",
        param=format_tezos_amount(fee),
        hold=True,
        hide_continue=True,
        icon_color=ui.BLUE,
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_register_delegate(ctx, address, fee):
    await confirm_hex(
        ctx,
        "confirm_register_delegate",
        title="Register delegate",
        subtitle="Fee: " + format_tezos_amount(fee),
        description="Address:",
        data=address,
        width=18,
        icon_color=ui.BLUE,
        br_code=ButtonRequestType.SignTx,
    )


def format_tezos_amount(value):
    formatted_value = format_amount(value, TEZOS_AMOUNT_DECIMALS)
    return formatted_value + " XTZ"


async def require_confirm_ballot(ctx, proposal, ballot):
    await confirm_hex(
        ctx,
        "confirm_ballot",
        title="Submit ballot",
        subtitle="Ballot: {}\nProposal:".format(ballot),
        data=proposal,
        width=17,
        truncate=True,
        icon_color=ui.PURPLE,
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_proposals(ctx, proposals):
    await confirm_proposals_tezos(ctx, proposals)


async def require_confirm_delegation_manager_withdraw(ctx, address):
    await confirm_hex(
        ctx,
        "confirm_undelegation",
        title="Remove delegation",
        subtitle="Delegator:",
        data=address,
        width=18,
        truncate=True,
        icon=ui.ICON_RECEIVE,
        icon_color=ui.RED,
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_manager_remove_delegate(ctx, fee):
    await confirm_metadata(
        ctx,
        "confirm_undelegation_final",
        title="Remove delegation",
        content="Fee:\n{}",
        param=format_tezos_amount(fee),
        hold=True,
        hide_continue=True,
        icon=ui.ICON_RECEIVE,
        icon_color=ui.RED,
        br_code=ButtonRequestType.SignTx,
    )
