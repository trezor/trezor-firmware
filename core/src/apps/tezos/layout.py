from trezor.enums import ButtonRequestType
from trezor.ui.layouts import confirm_address, confirm_metadata, confirm_properties

BR_SIGN_TX = ButtonRequestType.SignTx  # global_import_cache


async def require_confirm_tx(to: str, value: int, chunkify: bool = False) -> None:
    from trezor.ui.layouts import confirm_output

    await confirm_output(
        to,
        format_tezos_amount(value),
        br_code=BR_SIGN_TX,
        chunkify=chunkify,
    )


async def require_confirm_fee(value: int, fee: int) -> None:
    from trezor.ui.layouts import confirm_total

    await confirm_total(
        format_tezos_amount(value),
        format_tezos_amount(fee),
        total_label="Amount:",
    )


async def require_confirm_origination(address: str) -> None:
    await confirm_address(
        "Confirm origination",
        address,
        "Address:",
        "confirm_origination",
        BR_SIGN_TX,
    )


async def require_confirm_origination_fee(balance: int, fee: int) -> None:
    await confirm_properties(
        "confirm_origination_final",
        "Confirm origination",
        (
            ("Balance:", format_tezos_amount(balance)),
            ("Fee:", format_tezos_amount(fee)),
        ),
        hold=True,
    )


async def require_confirm_delegation_baker(baker: str) -> None:
    await confirm_address(
        "Confirm delegation",
        baker,
        "Baker address:",
        "confirm_delegation",
        BR_SIGN_TX,
    )


async def require_confirm_set_delegate(fee: int) -> None:
    await confirm_metadata(
        "confirm_delegation_final",
        "Confirm delegation",
        "Fee:\n{}",
        format_tezos_amount(fee),
        BR_SIGN_TX,
        hold=True,
    )


async def require_confirm_register_delegate(address: str, fee: int) -> None:
    await confirm_properties(
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


async def require_confirm_ballot(proposal: str, ballot: str) -> None:
    await confirm_properties(
        "confirm_ballot",
        "Submit ballot",
        (
            ("Ballot:", ballot),
            ("Proposal:", proposal),
        ),
        hold=True,
        br_code=BR_SIGN_TX,
    )


async def require_confirm_proposals(proposals: list[str]) -> None:
    await confirm_properties(
        "confirm_proposals",
        "Submit proposals" if len(proposals) > 1 else "Submit proposal",
        [("Proposal " + str(i), proposal) for i, proposal in enumerate(proposals, 1)],
        hold=True,
        br_code=BR_SIGN_TX,
    )


async def require_confirm_delegation_manager_withdraw(address: str) -> None:
    await confirm_address(
        "Remove delegation",
        address,
        "Delegator:",
        "confirm_undelegation",
        BR_SIGN_TX,
    )


async def require_confirm_manager_remove_delegate(fee: int) -> None:
    await confirm_metadata(
        "confirm_undelegation_final",
        "Remove delegation",
        "Fee:\n{}",
        format_tezos_amount(fee),
        BR_SIGN_TX,
        hold=True,
    )
