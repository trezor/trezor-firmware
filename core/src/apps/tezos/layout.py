from trezor import TR
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
        total_label=f"{TR.words__amount}:",
    )


async def require_confirm_origination(address: str) -> None:
    await confirm_address(
        TR.tezos__confirm_origination,
        address,
        description=TR.words__address,
        br_name="confirm_origination",
        br_code=BR_SIGN_TX,
    )


async def require_confirm_origination_fee(balance: int, fee: int) -> None:
    await confirm_properties(
        "confirm_origination_final",
        TR.tezos__confirm_origination,
        (
            (TR.tezos__balance, format_tezos_amount(balance)),
            (f"{TR.words__fee}:", format_tezos_amount(fee)),
        ),
        hold=True,
    )


async def require_confirm_delegation_baker(baker: str) -> None:
    await confirm_address(
        TR.tezos__confirm_delegation,
        baker,
        description=TR.tezos__baker_address,
        br_name="confirm_delegation",
        br_code=BR_SIGN_TX,
    )


async def require_confirm_set_delegate(fee: int) -> None:
    await confirm_metadata(
        "confirm_delegation_final",
        TR.tezos__confirm_delegation,
        f"{TR.words__fee}:\n{{}}",
        format_tezos_amount(fee),
        BR_SIGN_TX,
        hold=True,
    )


async def require_confirm_register_delegate(address: str, fee: int) -> None:
    await confirm_properties(
        "confirm_register_delegate",
        TR.tezos__register_delegate,
        (
            (f"{TR.words__fee}:", format_tezos_amount(fee)),
            (f"{TR.words__address}:", address),
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
        TR.tezos__submit_ballot,
        (
            (TR.tezos__ballot, ballot),
            (f"{TR.tezos__proposal}:", proposal),
        ),
        hold=True,
        br_code=BR_SIGN_TX,
    )


async def require_confirm_proposals(proposals: list[str]) -> None:
    await confirm_properties(
        "confirm_proposals",
        TR.tezos__submit_proposals if len(proposals) > 1 else TR.tezos__submit_proposal,
        [
            (f"{TR.tezos__proposal} " + str(i), proposal)
            for i, proposal in enumerate(proposals, 1)
        ],
        hold=True,
        br_code=BR_SIGN_TX,
    )


async def require_confirm_delegation_manager_withdraw(address: str) -> None:
    await confirm_address(
        TR.tezos__remove_delegation,
        address,
        description=TR.tezos__delegator,
        br_name="confirm_undelegation",
        br_code=BR_SIGN_TX,
    )


async def require_confirm_manager_remove_delegate(fee: int) -> None:
    await confirm_metadata(
        "confirm_undelegation_final",
        TR.tezos__remove_delegation,
        f"{TR.words__fee}:\n{{}}",
        format_tezos_amount(fee),
        BR_SIGN_TX,
        hold=True,
    )
