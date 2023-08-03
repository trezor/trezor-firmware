from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.utils import BufferReader

    Address = tuple[bytes, int]
    ProgramId = bytes
    Data = BufferReader
    Instruction = tuple[ProgramId, list[Address], Data]
