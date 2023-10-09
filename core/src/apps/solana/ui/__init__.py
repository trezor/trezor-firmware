from typing import TYPE_CHECKING

from trezor.crypto import base58

from ..transaction.instructions import Instruction
from ..constants import (
    ADDRESS_SIG,
    ADDRESS_SIG_READ_ONLY,
    ADDRESS_READ_ONLY,
    ADDRESS_RW
)

if TYPE_CHECKING:
    from typing import Any


def format_property(value: Any, type: str) -> str | bytes | None:
    if type in ("pubkey", "authority"):
        return base58.encode(value)
    elif isinstance(value, int):
        return str(value)

    return value


async def show_confirm(
    count: tuple[int, int], instruction: Instruction, signer: bytes
) -> None:
    from trezor.ui.layouts import confirm_properties

    # assertions for pyright
    assert instruction.parsed_data is not None
    assert instruction.parsed_accounts is not None
    assert instruction.ui_parameter_list is not None
    assert instruction.ui_account_list is not None

    datas = []
    for property in instruction.ui_parameter_list:
        property_template = instruction.get_property_template(property)
        ui_name = property_template["ui_name"]
        value = instruction.parsed_data[property]
        _type = property_template["type"]
        if _type == "authority":
            if signer == value:
                continue

        datas.append((ui_name, format_property(value, _type)))

    accounts = []
    for account in instruction.ui_account_list:
        account_template = instruction.get_account_template(account[0])[1]
        ui_name = account_template["ui_name"]
        is_authority = account_template["is_authority"]
        account_value = instruction.parsed_accounts[account[0]]

        if is_authority and account_value[0] == signer:
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

    props = datas + accounts

    return await confirm_properties(
        instruction.ui_identifier,
        f"{count[1]}/{count[0]}: {instruction.ui_name}",
        props,
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

def get_unknown_instruction_properties(instruction: Instruction) -> list[tuple[str, str | bytes]]:
    datas: list[tuple[str, str | bytes]] = []
    if len(instruction.instruction_data) == 0:
        datas.append(("Instruction data:", "not set"))
    # elif len(instruction.instruction_data) > 32:
    #     datas.append(("Instruction data:", instruction.instruction_data[:32]))
    else:
        datas.append(("Instruction data:", instruction.instruction_data))

    accounts = []
    for i, account in enumerate(instruction.accounts):
        accounts.append((f"Account {i + 1} {get_address_type(account[1])}:", base58.encode(account[0])))

    props = datas + accounts

    return props

async def show_unsupported_instruction_confirm(
    count: tuple[int, int], instruction: Instruction, signer: bytes
) -> None:
    from trezor.ui.layouts import confirm_properties

    return await confirm_properties(
        instruction.ui_identifier,
        f"{count[1]}/{count[0]}: {instruction.ui_name}: instruction id ({instruction.instruction_id})",
        get_unknown_instruction_properties(instruction)
    )


async def show_unsupported_program_confirm(
    count: tuple[int, int], instruction: Instruction, signer: bytes
) -> None:
    from trezor.ui.layouts import confirm_properties

    return await confirm_properties(
        instruction.ui_identifier,
        f"{count[1]}/{count[0]}: {instruction.ui_name}",
        [("Program", instruction.program_id)] + get_unknown_instruction_properties(instruction)
    )


async def show_final_confirmation(blockhash: bytes, fee: int) -> None:
    from trezor.ui.layouts import confirm_properties

    await confirm_properties(
        "sign_message", 
        "Sign message",
        [
            ("Blockhash", base58.encode(blockhash)),
            ("Fee", f"{fee} lamports")
        ]
    )
