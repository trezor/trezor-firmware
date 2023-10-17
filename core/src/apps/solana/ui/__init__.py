from typing import TYPE_CHECKING

from trezor.crypto import base58

from apps.common.paths import address_n_to_str

from ..constants import (
    ADDRESS_READ_ONLY,
    ADDRESS_RW,
    ADDRESS_SIG,
    ADDRESS_SIG_READ_ONLY,
)
from ..transaction.instructions import Instruction

if TYPE_CHECKING:
    from typing import Any


def format_property(value: Any, type: str) -> str | bytes | None:
    if type in ("pubkey", "authority"):
        return base58.encode(value)
    elif isinstance(value, int):
        return str(value)

    return value


async def show_confirm(
    instruction: Instruction,
    instructions_count: int,
    instruction_index: int,
    signer_path: list[int],
    signer_public_key: bytes,
) -> None:
    from trezor.enums import ButtonRequestType
    from trezor.ui.layouts import confirm_metadata, confirm_properties

    # assertions for pyright
    assert instruction.parsed_data is not None
    assert instruction.parsed_accounts is not None
    assert instruction.ui_parameter_list is not None
    assert instruction.ui_account_list is not None

    datas = []
    for property in instruction.ui_parameter_list:
        property_template = instruction.get_property_template(property)
        ui_name = property_template.ui_name
        value = instruction.parsed_data[property]
        _type = property_template.type
        if _type == "authority":
            if signer_public_key == value:
                continue

        datas.append((ui_name, format_property(value, _type)))

    if len(datas) > 0:
        await confirm_properties(
            "confirm_instruction",
            f"{instruction_index}/{instructions_count}: {instruction.ui_name}",
            datas,
        )

    accounts = []
    for account in instruction.ui_account_list:
        account_template = instruction.get_account_template(account[0])[1]
        ui_name = account_template.ui_name
        is_authority = account_template.is_authority
        account_value = instruction.parsed_accounts[account[0]]

        if is_authority and account_value[0] == signer_public_key:
            continue

        if len(account_value) == 2:
            accounts.append((ui_name, base58.encode(account_value[0])))
        elif len(account_value) == 3:
            accounts.append(
                (
                    ui_name,
                    f"LUT: {base58.encode(account_value[0])}, index: {account_value[1]}",
                )
            )
        else:
            raise ValueError("Invalid account value")

    if len(accounts) > 0:
        await confirm_properties(
            "confirm_instruction",
            f"{instruction_index}/{instructions_count}: {instruction.ui_name}",
            accounts,
        )

    if instruction.is_multisig:
        await confirm_metadata(
            "confirm_multisig",
            "Confirm multisig",
            "The following instruction is a multisig instruction.",
            br_code=ButtonRequestType.Other,
        )

        assert instruction.multisig_signers is not None

        signers: list[tuple[str, str]] = []
        for i, multisig_signer in enumerate(instruction.multisig_signers, 1):
            multisig_signer_public_key = multisig_signer[0]

            path_str = ""
            if multisig_signer_public_key == signer_public_key:
                path_str = f" ({address_n_to_str(signer_path)})"

            signers.append(
                (f"Signer {i}{path_str}:", base58.encode(multisig_signer[0]))
            )

        await confirm_properties(
            "confirm_instruction",
            f"{instruction_index}/{instructions_count}: {instruction.ui_name}",
            signers,
        )


def get_address_type(address_type: int) -> str:
    if ADDRESS_SIG == address_type:
        return "(Writable, Signer)"
    elif ADDRESS_SIG_READ_ONLY == address_type:
        return "(Signer)"
    elif ADDRESS_READ_ONLY == address_type:
        return ""
    elif ADDRESS_RW == address_type:
        return "(Writable)"
    else:
        raise ValueError(f"Invalid address type {address_type}")


async def show_unsupported_instruction_details(
    instruction: Instruction,
    title: str,
    signer_path: list[int],
    signer_public_key: bytes,
) -> None:
    from trezor.ui import NORMAL
    from trezor.ui.layouts import confirm_properties, should_show_more

    assert instruction.instruction_data is not None
    assert instruction.accounts is not None

    should_show_instruction_details = await should_show_more(
        title,
        (
            (
                NORMAL,
                f"Instruction contains {len(instruction.accounts)} accounts and its data is {len(instruction.instruction_data)} bytes long.",
            ),
        ),
        "Show details",
        confirm="Continue",
    )

    if should_show_instruction_details:
        await confirm_properties(
            "instruction_data",
            title,
            (("Instruction data:", instruction.instruction_data),),
        )

        accounts = []
        for i, account in enumerate(instruction.accounts, 1):
            account_public_key = account[0]
            address_type = get_address_type(account[1])

            path_str = ""
            if account_public_key == signer_public_key:
                path_str = f" ({address_n_to_str(signer_path)})"

            accounts.append(
                (
                    f"Account {i}{path_str} {address_type}:",
                    base58.encode(account_public_key),
                )
            )

        await confirm_properties(
            "accounts",
            title,
            accounts,
        )


async def show_unsupported_instruction_confirm(
    instruction: Instruction,
    instructions_count: int,
    instruction_index: int,
    signer_path: list[int],
    signer_public_key: bytes,
) -> None:
    title = f"{instruction_index}/{instructions_count}: {instruction.ui_name}: instruction id ({instruction.instruction_id})"

    return await show_unsupported_instruction_details(
        instruction, title, signer_path, signer_public_key
    )


async def show_unsupported_program_confirm(
    instruction: Instruction,
    instructions_count: int,
    instruction_index: int,
    signer_path: list[int],
    signer_public_key: bytes,
) -> None:
    title = f"{instruction_index}/{instructions_count}: {instruction.ui_name}"

    return await show_unsupported_instruction_details(
        instruction, title, signer_path, signer_public_key
    )


async def show_final_confirmation(
    signer_path: str, address: str, blockhash: bytes, fee: int
) -> None:
    from trezor.ui.layouts import confirm_properties

    await confirm_properties(
        "confirm_transaction",
        "Confirm transaction",
        [
            ("Fee:", f"{fee} lamports"),
            ("Blockhash:", base58.encode(blockhash)),
            ("Signer Path:", signer_path),
            ("Signer Address:", address),
        ],
    )
