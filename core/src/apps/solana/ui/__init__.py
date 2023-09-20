from typing import TYPE_CHECKING

from trezor.crypto import base58

from ..transaction.instructions import Instruction

if TYPE_CHECKING:
    from typing import Any


def format_property(value: Any, type: str) -> str | bytes | None:
    if type == "pubkey":
        return base58.encode(value)
    elif isinstance(value, int):
        return str(value)

    return value


async def show_confirm(count: tuple[int, int], instruction: Instruction) -> None:
    from trezor.ui.layouts import confirm_properties

    # assertions for pyright
    assert instruction.parsed_data is not None
    assert instruction.parsed_accounts is not None
    assert instruction.ui_parameter_list is not None
    assert instruction.ui_account_list is not None

    datas = []
    for property in instruction.ui_parameter_list:
        value = instruction.parsed_data[property]
        _type = instruction.get_property_type(property)

        datas.append((property, format_property(value, _type)))

    accounts = []
    for account in instruction.ui_account_list:
        account_value = instruction.parsed_accounts[account[0]]

        if len(account_value) == 2:
            accounts.append((account[0], base58.encode(account_value[0])))
        elif len(account_value) == 3:
            accounts.append(
                (
                    account[0],
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
