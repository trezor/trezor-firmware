from ..transaction.instructions import Instruction

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any

def get_ui_property(property: Any) -> str | bytes | None:
    if isinstance(property, int):
        return str(property)
    
    return property

async def show_confirm(instruction: Instruction) -> None:
    from trezor.ui.layouts import confirm_properties

    # assertions for pyright
    assert instruction.parsed_data is not None
    assert instruction.parsed_accounts is not None

    datas = []

    for prop in instruction.ui_parameter_list:
        datas.append(
            (
                prop, get_ui_property(instruction.parsed_data[prop])
            )
        )

    accounts = []
    # TODO SOL: handle accounts
    # for account in instruction.accounts_template:
    #     account_value = instruction.parsed_accounts[account[0]]
    #     if account_value is not None:
    #         accounts.append((account[1], account_value))

    props = datas + accounts

    return await confirm_properties(
        instruction.ui_identifier, instruction.ui_name, props
    )
