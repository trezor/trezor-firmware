from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import TypedDict

    Address = tuple[bytes, int]
    AddressReference = tuple[bytes, int, int]
    Account = Address | AddressReference

    ProgramIndex = int
    InstructionId = int
    AccountIndex = int
    Data = memoryview
    RawInstruction = tuple[ProgramIndex, InstructionId, list[AccountIndex], Data]

    class InstructionIdFormat(TypedDict):
        length: int
        is_included_if_zero: bool
