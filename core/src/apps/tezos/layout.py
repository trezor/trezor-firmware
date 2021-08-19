from typing import TYPE_CHECKING

from trezor import ui
from trezor.enums import ButtonRequestType
from trezor.strings import format_amount
from trezor.ui.layouts import (
    confirm_address,
    confirm_metadata,
    confirm_output,
    confirm_properties,
    confirm_total,
)

from .helpers import TEZOS_AMOUNT_DECIMALS

if TYPE_CHECKING:
    from trezor.wire import Context


async def require_confirm_tx(ctx: Context, to: str, value: int) -> None:
    await confirm_output(
        ctx,
        to,
        format_tezos_amount(value),
        font_amount=ui.BOLD,
        to_str="\nto\n",
        width=18,
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_fee(ctx: Context, value: int, fee: int) -> None:
    await confirm_total(
        ctx,
        total_amount=format_tezos_amount(value),
        total_label="Amount:\n",
        fee_amount=format_tezos_amount(fee),
        fee_label="\nFee:\n",
    )


async def require_confirm_origination(ctx: Context, address: str) -> None:
    await confirm_address(
        ctx,
        title="Confirm origination",
        address=address,
        description="Address:",
        name="confirm_origination",
        icon_color=ui.ORANGE,
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_origination_fee(ctx: Context, balance: int, fee: int) -> None:
    await confirm_properties(
        ctx,
        title="Confirm origination",
        props=(
            ("Balance:", format_tezos_amount(balance)),
            ("Fee:", format_tezos_amount(fee)),
        ),
        icon_color=ui.ORANGE,
        name="confirm_origination_final",
        hold=True,
    )


async def require_confirm_delegation_baker(ctx: Context, baker: str) -> None:
    await confirm_address(
        ctx,
        title="Confirm delegation",
        address=baker,
        description="Baker address:",
        name="confirm_delegation",
        icon_color=ui.BLUE,
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_set_delegate(ctx: Context, fee: int) -> None:
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


async def require_confirm_register_delegate(
    ctx: Context, address: str, fee: int
) -> None:
    await confirm_properties(
        ctx,
        "confirm_register_delegate",
        title="Register delegate",
        props=(
            ("Fee:", format_tezos_amount(fee)),
            ("Address:", address),
        ),
        icon_color=ui.BLUE,
        br_code=ButtonRequestType.SignTx,
    )


def format_tezos_amount(value: int) -> str:
    formatted_value = format_amount(value, TEZOS_AMOUNT_DECIMALS)
    return formatted_value + " XTZ"


async def require_confirm_ballot(ctx: Context, proposal: str, ballot: str) -> None:
    await confirm_properties(
        ctx,
        "confirm_ballot",
        title="Submit ballot",
        props=(
            ("Ballot:", ballot),
            ("Proposal:", proposal),
        ),
        icon_color=ui.PURPLE,
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_proposals(ctx: Context, proposals: list[str]) -> None:
    if len(proposals) > 1:
        title = "Submit proposals"
    else:
        title = "Submit proposal"

    await confirm_properties(
        ctx,
        "confirm_proposals",
        title=title,
        props=[
            ("Proposal " + str(i), proposal) for i, proposal in enumerate(proposals, 1)
        ],
        icon_color=ui.PURPLE,
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_delegation_manager_withdraw(
    ctx: Context, address: str
) -> None:
    await confirm_address(
        ctx,
        title="Remove delegation",
        address=address,
        description="Delegator:",
        name="confirm_undelegation",
        icon=ui.ICON_RECEIVE,
        icon_color=ui.RED,
        br_code=ButtonRequestType.SignTx,
    )


async def require_confirm_manager_remove_delegate(ctx: Context, fee: int) -> None:
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
