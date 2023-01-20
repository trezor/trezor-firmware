from typing import TYPE_CHECKING

from trezor.enums import ButtonRequestType
from trezor.ui.layouts import confirm_address, confirm_metadata, confirm_properties

if TYPE_CHECKING:
    from trezor.wire import Context


BR_SIGN_TX = ButtonRequestType.SignTx  # global_import_cache


async def require_confirm_tx(ctx: Context, to: str, value: int) -> None:
    from trezor.ui.layouts import confirm_output

    await confirm_output(
        ctx,
        to,
        format_tezos_amount(value),
        br_code=BR_SIGN_TX,
    )


async def require_confirm_fee(ctx: Context, value: int, fee: int) -> None:
    from trezor.ui.layouts import confirm_total

    await confirm_total(
        ctx,
        format_tezos_amount(value),
        format_tezos_amount(fee),
        total_label="Amount:",
    )


async def require_confirm_origination(ctx: Context, address: str) -> None:
    await confirm_address(
        ctx,
        "Confirm origination",
        address,
        "Address:",
        "confirm_origination",
        BR_SIGN_TX,
    )


async def require_confirm_origination_fee(ctx: Context, balance: int, fee: int) -> None:
    await confirm_properties(
        ctx,
        "confirm_origination_final",
        "Confirm origination",
        (
            ("Balance:", format_tezos_amount(balance)),
            ("Fee:", format_tezos_amount(fee)),
        ),
        hold=True,
    )


async def require_confirm_delegation_baker(ctx: Context, baker: str) -> None:
    await confirm_address(
        ctx,
        "Confirm delegation",
        baker,
        "Baker address:",
        "confirm_delegation",
        BR_SIGN_TX,
    )


async def require_confirm_set_delegate(ctx: Context, fee: int) -> None:
    await confirm_metadata(
        ctx,
        "confirm_delegation_final",
        "Confirm delegation",
        "Fee:\n{}",
        format_tezos_amount(fee),
        BR_SIGN_TX,
        hold=True,
    )


async def require_confirm_register_delegate(
    ctx: Context, address: str, fee: int
) -> None:
    await confirm_properties(
        ctx,
        "confirm_register_delegate",
        "Register delegate",
        (
            ("Fee:", format_tezos_amount(fee)),
            ("Address:", address),
        ),
        hold=True,
        br_code=BR_SIGN_TX,
    )


def format_tezos_amount(value: int) -> str:
    from trezor.strings import format_amount
    from .helpers import TEZOS_AMOUNT_DECIMALS

    formatted_value = format_amount(value, TEZOS_AMOUNT_DECIMALS)
    return formatted_value + " XTZ"


async def require_confirm_ballot(ctx: Context, proposal: str, ballot: str) -> None:
    await confirm_properties(
        ctx,
        "confirm_ballot",
        "Submit ballot",
        (
            ("Ballot:", ballot),
            ("Proposal:", proposal),
        ),
        hold=True,
        br_code=BR_SIGN_TX,
    )


async def require_confirm_proposals(ctx: Context, proposals: list[str]) -> None:
    await confirm_properties(
        ctx,
        "confirm_proposals",
        "Submit proposals" if len(proposals) > 1 else "Submit proposal",
        [("Proposal " + str(i), proposal) for i, proposal in enumerate(proposals, 1)],
        hold=True,
        br_code=BR_SIGN_TX,
    )


async def require_confirm_delegation_manager_withdraw(
    ctx: Context, address: str
) -> None:
    await confirm_address(
        ctx,
        "Remove delegation",
        address,
        "Delegator:",
        "confirm_undelegation",
        BR_SIGN_TX,
    )


async def require_confirm_manager_remove_delegate(ctx: Context, fee: int) -> None:
    await confirm_metadata(
        ctx,
        "confirm_undelegation_final",
        "Remove delegation",
        "Fee:\n{}",
        format_tezos_amount(fee),
        BR_SIGN_TX,
        hold=True,
    )
