from typing import TYPE_CHECKING

from trezor.crypto import base58

from ..transaction.instructions import Instruction

if TYPE_CHECKING:
    from typing import Any


def get_ui_property(property: Any) -> str | bytes | None:
    if isinstance(property, int):
        return str(property)

    return property


async def show_confirm(count: tuple[int, int], instruction: Instruction) -> None:
    from trezor.ui.layouts import confirm_properties

    # assertions for pyright
    assert instruction.parsed_data is not None
    assert instruction.parsed_accounts is not None
    assert instruction.ui_parameter_list is not None
    assert instruction.ui_account_list is not None

    datas = []
    for prop in instruction.ui_parameter_list:
        # TODO SOL: public keys in params are not base58 encoded
        datas.append((prop, get_ui_property(instruction.parsed_data[prop])))

    accounts = []
    for account in instruction.ui_account_list:
        account_value = instruction.parsed_accounts[account[0]]
        # TODO SOL:
        if type(account_value) is bytes:
            accounts.append((account[0], base58.encode(account_value)))
        elif type(account_value) is tuple:
            accounts.append((account[0], base58.encode(account_value[0])))

    props = datas + accounts

    return await confirm_properties(
        instruction.ui_identifier,
        f"{count[0]}/{count[1]}: {instruction.ui_name}",
        props,
    )
