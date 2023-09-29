from typing import TYPE_CHECKING

from trezor.crypto import base58
from trezor.strings import format_amount
from trezor.ui import layouts

from ..transaction.instructions import Instruction, TransferInstruction

if TYPE_CHECKING:
    from typing import Any


def format_property(value: Any, type: str) -> str | bytes | None:
    if type == "pubkey" or type == "authority":
        return base58.encode(value)
    elif isinstance(value, int):
        return str(value)

    return value


async def show_confirm(
    count: tuple[int, int], instruction: Instruction, signer: bytes
) -> None:
    from trezor.ui.layouts import confirm_properties

    if TransferInstruction.is_type_of(instruction):
        print(instruction.funding_account, signer)
        if instruction.funding_account[0] != signer:
            raise ValueError("Invalid funding account")

        return await layouts.confirm_output(
            base58.encode(instruction.recipient_account[0]),
            f"{format_amount(instruction.lamports, 8)} SOL",
        )

    # assertions for pyright
    assert instruction.parsed_data is not None
    assert instruction.parsed_accounts is not None
    assert instruction.ui_parameter_list is not None
    assert instruction.ui_account_list is not None

    datas = []
    for property in instruction.ui_parameter_list:
        ui_name = instruction.property_templates[property]["ui_name"]
        value = instruction.parsed_data[property]
        _type = instruction.property_templates[property]["type"]

        if _type == "authority":
            if signer == value:
                continue

        datas.append((ui_name, format_property(value, _type)))

    accounts = []
    for account in instruction.ui_account_list:
        ui_name = instruction.accounts_template[account[0]]["ui_name"]
        is_authority = instruction.accounts_template[account[0]]["is_authority"]
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
        f"{count[0]}/{count[1]}: {instruction.ui_name}",
        props,
    )
