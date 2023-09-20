from typing import TYPE_CHECKING

from trezor.crypto import base58
from trezor.utils import BufferReader

from .parse import parseProperty

if TYPE_CHECKING:
    from typing import Any, TypedDict, TypeGuard
    from ..types import Account

    class PropertyTemplate(TypedDict):
        name: str
        type: str
        optional: bool

    class AccountsTemplate(TypedDict):
        name: str
        access: str
        signer: bool
        optional: bool


class Instruction:
    PROGRAM_ID: str
    INSTRUCTION_ID: int

    program_id: bytes
    instruction_id: int

    property_templates: list[PropertyTemplate]
    accounts_template: list[AccountsTemplate]

    # name of the UI template to be used derived from the template
    ui_identifier: str
    # Name to be displayed on the UI
    ui_name: str

    # There is no separate field for UI display name, so the property name is used
    # for that purpose. The values within this list shall be used to display on the
    # UI and to retrieve the value by calling the __getattr__ function.
    ui_parameter_list: list[str] | None = None
    # Here, a tuple is used where the first item is the UI Display name and the
    # second item is the account name that can be used to retrieve the value
    # by using the __getattr__ function or access directly from the parsed_accounts
    # list.
    ui_account_list: list[tuple[str, Account]] | None = None

    parsed_data: dict[str, Any] | None = None
    parsed_accounts: dict[str, Account] | None = None

    def __init__(
        self,
        instruction_data: bytes,
        program_id: bytes,
        accounts: list[Account],
        instruction_id: int,
        property_templates: list[PropertyTemplate],
        accounts_template: list[AccountsTemplate],
        ui_parameter_list: list[int],
        ui_account_list: list[int],
        ui_identifier: str,
        ui_name: str,
    ) -> None:
        self.program_id = program_id
        self.instruction_id = instruction_id

        self.property_templates = property_templates
        self.accounts_template = accounts_template

        self.ui_identifier = ui_identifier
        self.ui_name = ui_name

        self.ui_parameter_list = []
        self.ui_account_list = []

        self.parsed_data = {}
        self.parsed_accounts = {}

        reader = BufferReader(instruction_data)

        for property_template in property_templates:
            self.set_property(
                property_template["name"],
                parseProperty(reader, property_template["type"]),
            )

        for i, account_template in enumerate(accounts_template):
            if i >= len(accounts):
                if account_template["optional"]:
                    continue
                else:
                    raise ValueError("Missing account")

            self.set_account(account_template["name"], accounts[i])

        for parameter_index in ui_parameter_list:
            self.ui_parameter_list.append(property_templates[parameter_index]["name"])

        for account_index in ui_account_list:
            if account_index >= len(accounts):
                if self.accounts_template[account_index]["optional"]:
                    continue
                else:
                    raise ValueError("Missing account")

            self.ui_account_list.append(
                (accounts_template[account_index]["name"], accounts[account_index])
            )

    def __getattr__(self, attr: str) -> Any:
        assert self.parsed_data is not None
        assert self.parsed_accounts is not None

        if attr in self.parsed_data:
            return self.parsed_data[attr]
        elif attr in self.parsed_accounts:
            return self.parsed_accounts[attr]
        else:
            raise AttributeError(f"Attribute {attr} not found")

    def set_property(self, attr: str, value: Any) -> None:
        assert self.parsed_data is not None
        self.parsed_data[attr] = value

    def set_account(self, account: str, value: Account) -> None:
        assert self.parsed_accounts is not None
        self.parsed_accounts[account] = value

    # TODO SOL: maybe property template could be a dict[name, prop] instead of a list[prop]
    def get_property_type(self, property: str) -> str:
        for property_template in self.property_templates:
            print(property_template, property)
            if property_template["name"] == property:
                return property_template["type"]

        raise ValueError(f"Property {property} not found")

    @classmethod
    def is_type_of(cls, ins: Any) -> TypeGuard["Instruction"]:
        return (
            base58.encode(ins.program_id) == cls.PROGRAM_ID
            and ins.instruction_id == cls.INSTRUCTION_ID
        )
