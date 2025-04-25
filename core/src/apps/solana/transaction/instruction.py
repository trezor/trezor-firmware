from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, TypeGuard

    from typing_extensions import Self

    from ..types import Account, InstructionData, PropertyTemplate, UIProperty


class Instruction:
    program_id: str
    instruction_id: int | None

    property_templates: tuple[PropertyTemplate, ...]
    accounts_required: int
    account_templates: tuple[str, ...]

    ui_name: str

    ui_properties: tuple[UIProperty, ...]

    parsed_data: dict[str, Any]
    parsed_accounts: dict[str, Account]

    is_program_supported: bool
    is_instruction_supported: bool
    is_ui_hidden: bool
    instruction_data: InstructionData
    accounts: list[Account]

    multisig_signers: list[Account]

    is_deprecated_warning: str | None = None

    @staticmethod
    def parse_instruction_data(
        instruction_data: InstructionData,
        property_templates: tuple[PropertyTemplate, ...],
    ) -> dict[str, Any]:
        from trezor.utils import BufferReader
        from trezor.wire import DataError

        reader = BufferReader(instruction_data)

        parsed_data = {}
        for property_template in property_templates:
            is_included = True
            if property_template.optional:
                is_included = True if reader.get() == 1 else False

            parsed_data[property_template.name] = (
                property_template.parse(reader) if is_included else None
            )

        if reader.remaining_count() != 0:
            raise DataError("Invalid transaction data")

        return parsed_data

    @staticmethod
    def parse_instruction_accounts(
        accounts: list[Account],
        accounts_required: int,
        account_templates: tuple[str, ...],
    ) -> dict[str, Account]:
        parsed_accounts = {}
        if len(accounts) < accounts_required:
            raise ValueError  # "Account is missing

        for i, account_name in enumerate(account_templates):
            if i >= len(accounts):
                break
            parsed_accounts[account_name] = accounts[i]
        return parsed_accounts

    def __init__(
        self,
        instruction_data: InstructionData,
        program_id: str,
        accounts: list[Account],
        instruction_id: int | None,
        property_templates: tuple[PropertyTemplate, ...],
        accounts_required: int,
        account_templates: tuple[str, ...],
        ui_properties: tuple[UIProperty, ...],
        ui_name: str,
        is_program_supported: bool = True,
        is_instruction_supported: bool = True,
        is_ui_hidden: bool = False,
        supports_multisig: bool = False,
        is_deprecated_warning: str | None = None,
    ) -> None:
        self.program_id = program_id
        self.instruction_id = instruction_id

        self.property_templates = property_templates
        self.accounts_required = accounts_required
        self.account_templates = account_templates

        self.ui_name = ui_name

        self.ui_properties = ui_properties

        self.is_ui_hidden = is_ui_hidden
        self.is_program_supported = is_program_supported
        self.is_instruction_supported = is_instruction_supported

        self.is_deprecated_warning = is_deprecated_warning

        self.instruction_data = instruction_data
        self.accounts = accounts

        if self.is_instruction_supported:
            self.parsed_data = self.parse_instruction_data(
                instruction_data, property_templates
            )

            self.parsed_accounts = self.parse_instruction_accounts(
                accounts,
                accounts_required,
                account_templates,
            )

            self.multisig_signers = accounts[len(account_templates) :]
            if self.multisig_signers and not supports_multisig:
                raise ValueError  # Multisig not supported
        else:
            self.parsed_data = {}
            self.parsed_accounts = {}
            self.multisig_signers = []

    def __getattr__(self, attr: str) -> Any:
        if attr in self.parsed_data:
            return self.parsed_data[attr]
        if attr in self.parsed_accounts:
            return self.parsed_accounts[attr]

        raise AttributeError  # Attribute not found

    def get_property_template(self, property: str) -> PropertyTemplate:
        for property_template in self.property_templates:
            if property_template.name == property:
                return property_template

        raise ValueError  # Property not found

    @classmethod
    def is_type_of(cls, ins: Any) -> TypeGuard[Self]:
        # gets overridden in `instructions.py` `FakeClass`
        raise NotImplementedError
