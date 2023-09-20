from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.utils import BufferReader

    Address = tuple[bytes, int]
    AddressReference = tuple[bytes, int, int]
    Account = Address | AddressReference
    ProgramId = bytes
    Data = BufferReader
    RawInstruction = tuple[ProgramId, list[Account], Data]
