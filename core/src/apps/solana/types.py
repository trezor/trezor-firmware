from typing import TYPE_CHECKING

if TYPE_CHECKING:
    Address = tuple[bytes, int]
    AddressReference = tuple[bytes, int, int]
    Account = Address | AddressReference

    ProgramIndex = int
    InstructionId = int
    AccountIndex = int
    Data = memoryview
    RawInstruction = tuple[ProgramIndex, InstructionId, list[AccountIndex], Data]


class InstructionIdFormat:
    length: int
    is_included_if_zero: bool

    def __init__(self, length: int, is_included_if_zero: bool):
        self.length = length
        self.is_included_if_zero = is_included_if_zero


class PropertyTemplate:
    name: str
    ui_name: str
    type: str
    optional: bool

    def __init__(self, name: str, ui_name: str, type: str, optional: bool):
        self.name = name
        self.ui_name = ui_name
        self.type = type
        self.optional = optional


class AccountTemplate:
    name: str
    ui_name: str
    is_authority: bool
    optional: bool

    def __init__(self, name: str, ui_name: str, is_authority: bool, optional: bool):
        self.name = name
        self.ui_name = ui_name
        self.is_authority = is_authority
        self.optional = optional
