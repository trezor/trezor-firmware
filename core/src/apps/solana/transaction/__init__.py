from typing import TYPE_CHECKING

from trezor.crypto import base58
from .parse import (
    parseHeader,
    parseAddresses,
    parseBlockHash,
    parseInstructions,
    parseLut
)
from .instructions import (
    get_instruction,
    Instruction
)

if TYPE_CHECKING:
    from trezor.utils import BufferReader
    from ..types import Address, AddressReference, RawInstruction

class Transaction:
    is_legacy: bool
    version: int

    # tuple[bytes, int] where int is the the address type derived from types.py:
    # 0 - ADDRESS_SIG
    # 1 - ADDRESS_SIG_READ_ONLY
    # 2 - ADDRESS_READ_ONLY
    # 3 - ADDRESS_RW
    addresses: list[Address]

    blockhash: bytes

    instructions: list[Instruction] = []

    # LUT parsing result comes here in case of non-legacy transaction
    lut_rw_addresses: tuple[Address, int] = None
    lut_ro_addresses: tuple[Address, int] = None

    def __init__(
        self,
        serialized_tx: BufferReader
    ) -> None:
        (
            self.is_legacy,
            self.version,
            num_required_signatures,
            num_signature_read_only_addresses,
            num_read_only_addresses
        ) = parseHeader(serialized_tx)

        self.addresses = parseAddresses(
            serialized_tx,
            num_required_signatures,
            num_signature_read_only_addresses,
            num_read_only_addresses
        )

        self.blockhash = parseBlockHash(serialized_tx)

        raw_instructions = parseInstructions(serialized_tx)
        for (program_index, instruction_id, accounts, instruction_data) in raw_instructions:
            program_id = self.addresses[program_index][0]
            instruction_accounts = [self.addresses[account_index] for account_index in accounts]
            instruction = get_instruction(program_id, instruction_id, instruction_accounts, instruction_data)
            self.instructions.append(instruction)
        
        if not self.is_legacy:
            (self.lut_rw_addresses, self.lut_ro_addresses) = parseLut(serialized_tx)
        
        assert serialized_tx.remaining_count() == 0