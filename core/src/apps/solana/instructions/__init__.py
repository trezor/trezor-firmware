from typing import TYPE_CHECKING

from trezor.crypto import base58

if TYPE_CHECKING:
    from typing import Any, TypeGuard
    from trezor.utils import BufferReader
    from ..types import Address, AddressReference, RawInstruction

SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"
STAKE_PROGRAM_ID = "Stake11111111111111111111111111111111111111"

SYSTEM_TRANSFER_ID = 2


class Instruction:
    PROGRAM_ID: str
    INSTRUCTION_ID: int

    ui_identifier: str
    ui_name: str

    program_id: str
    accounts: list[Address | AddressReference]
    data: BufferReader

    instruction_id: int
    data_template: list[tuple[str, str] | tuple[str, str, bool]]
    accounts_template: list[tuple[str, str, int] | tuple[str, str, int, bool]]

    parsed_data: dict[str, Any] | None = None
    parsed_accounts: dict[str, bytes | tuple[bytes, int] | None] | None = None

    def __init__(
        self,
        raw_instruction: RawInstruction,
        instruction_id: int,
        data_template: list[tuple[str, str] | tuple[str, str, bool]],
        accounts_template: list[tuple[str, str, int] | tuple[str, str, int, bool]],
        ui_identifier: str,
        ui_name: str,
    ):
        raw_program_id, self.accounts, self.data = raw_instruction
        self.program_id = base58.encode(raw_program_id)

        self.instruction_id = instruction_id

        self.data_template = data_template
        self.accounts_template = accounts_template

        self.ui_identifier = ui_identifier
        self.ui_name = ui_name

        self.parsed_data = {}
        self.parsed_accounts = {}

    def __getattr__(self, attr: str) -> Any:
        assert self.parsed_data is not None
        assert self.parsed_accounts is not None

        if attr in self.parsed_data:
            return self.parsed_data[attr]
        elif attr in self.parsed_accounts:
            return self.parsed_accounts[attr]
        else:
            # TODO SOL - what to do? object.__getattribute__ doesn't seem to work
            raise AttributeError(f"Attribute {attr} not found")

    def set_parsed_data(self, attr: str, value: Any) -> None:
        assert self.parsed_data is not None
        self.parsed_data[attr] = value

    def set_parsed_account(
        self, account: str, value: bytes | tuple[bytes, int] | None
    ) -> None:
        assert self.parsed_accounts is not None
        self.parsed_accounts[account] = value

    @classmethod
    def is_type_of(cls, ins: Any) -> TypeGuard["Instruction"]:
        return ins.program_id == cls.PROGRAM_ID and ins.type == cls.INSTRUCTION_ID
