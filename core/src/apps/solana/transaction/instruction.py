from typing import TYPE_CHECKING

from trezor.utils import BufferReader
from trezor.wire import ProcessError

from .parse import parse_property

if TYPE_CHECKING:
    from typing import Any, TypeGuard

    from ..types import Account, AccountTemplate, PropertyTemplate


class Instruction:
    PROGRAM_ID: str
    INSTRUCTION_ID: int

    program_id: str
    instruction_id: int

    property_templates: list[PropertyTemplate]
    accounts_template: list[AccountTemplate]

    ui_identifier: str
    ui_name: str

    ui_parameter_list: list[str] | None = None
    ui_account_list: list[tuple[str, Account]] | None = None

    parsed_data: dict[str, Any] | None = None
    parsed_accounts: dict[str, Account] | None = None

    is_program_supported: bool
    is_instruction_supported: bool
    instruction_data: bytes | None = None
    accounts: list[Account] | None = None

    is_multisig: bool = False
    multisig_signers: list[Account] | None = None

    def __init__(
        self,
        instruction_data: bytes,
        program_id: str,
        accounts: list[Account],
        instruction_id: int,
        property_templates: list[PropertyTemplate],
        accounts_template: list[AccountTemplate],
        ui_parameter_list: list[str],
        ui_account_list: list[str],
        ui_identifier: str,
        ui_name: str,
        is_program_supported: bool = True,
        is_instruction_supported: bool = True,
        supports_multisig: bool = False,
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

        self.is_program_supported = is_program_supported
        self.is_instruction_supported = is_instruction_supported

        # self.is_multisig = is_multisig

        reader = BufferReader(instruction_data)

        if not is_instruction_supported:
            self.instruction_data = reader.read()
            self.accounts = accounts

        for property_template in property_templates:
            self.set_property(
                property_template.name,
                parse_property(reader, property_template.type),
            )

        for i, account_template in enumerate(accounts_template):
            if i >= len(accounts):
                if account_template.optional:
                    continue
                else:
                    raise ValueError(f"Account {account_template.name} is missing")

            self.set_account(account_template.name, accounts[i])

        if supports_multisig and len(accounts) > len(accounts_template):
            self.is_multisig = True
            self.multisig_signers = accounts[len(accounts_template) :]

        for parameter in ui_parameter_list:
            self.ui_parameter_list.append(parameter)

        for account in ui_account_list:
            account_index, account_template = self.get_account_template(account)
            if account_index >= len(accounts):
                if account_template.optional:
                    continue
                else:
                    raise ValueError(f"Account {account_template.name} is missing")

            self.ui_account_list.append((account, accounts[account_index]))

        if reader.remaining_count() != 0:
            raise ProcessError("Invalid transaction")

    def __getattr__(self, attr: str) -> Any:
        assert self.parsed_data is not None
        assert self.parsed_accounts is not None

        if attr in self.parsed_data:
            return self.parsed_data[attr]
        if attr in self.parsed_accounts:
            return self.parsed_accounts[attr]

        raise AttributeError(f"Attribute {attr} not found")

    def set_property(self, attr: str, value: Any) -> None:
        assert self.parsed_data is not None
        self.parsed_data[attr] = value

    def set_account(self, account: str, value: Account) -> None:
        assert self.parsed_accounts is not None
        self.parsed_accounts[account] = value

    def get_property_template(self, property: str) -> PropertyTemplate:
        for property_template in self.property_templates:
            if property_template.name == property:
                return property_template

        raise ValueError(f"Property {property} not found")

    def get_account_template(self, account_name: str) -> tuple[int, AccountTemplate]:
        for i, template in enumerate(self.accounts_template):
            if template.name == account_name:
                return i, template

        raise ValueError(f"Account {account_name} not found")

    @classmethod
    def is_type_of(cls, ins: Any) -> TypeGuard["Instruction"]:
        return (
            ins.program_id == cls.PROGRAM_ID
            and ins.instruction_id == cls.INSTRUCTION_ID
        )
