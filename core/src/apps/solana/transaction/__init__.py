from typing import TYPE_CHECKING

from trezor.crypto import base58
from trezor.utils import BufferReader

from .instruction import Instruction
from .instructions import get_instruction, get_instruction_id_length
from .parse import (
    parseAddresses,
    parseBlockHash,
    parseHeader,
    parseInstructions,
    parseLut,
)

if TYPE_CHECKING:
    from ..types import Account, Address, AddressReference


class Transaction:
    is_legacy: bool
    version: int

    addresses: list[Address]

    blockhash: bytes

    instructions: list[Instruction] = []

    lut_rw_addresses: list[AddressReference] | None = None
    lut_ro_addresses: list[AddressReference] | None = None

    def __init__(self, serialized_tx: BufferReader) -> None:
        (
            self.is_legacy,
            self.version,
            num_required_signatures,
            num_signature_read_only_addresses,
            num_read_only_addresses,
        ) = parseHeader(serialized_tx)

        self.addresses = parseAddresses(
            serialized_tx,
            num_required_signatures,
            num_signature_read_only_addresses,
            num_read_only_addresses,
        )

        self.blockhash = parseBlockHash(serialized_tx)

        raw_instructions = parseInstructions(
            self.addresses, get_instruction_id_length, serialized_tx
        )

        addresses_and_luts: list[Account] = []
        for address in self.addresses:
            addresses_and_luts.append(address)

        if not self.is_legacy:
            self.lut_rw_addresses, self.lut_ro_addresses = parseLut(serialized_tx)
            for lut_rw_address in self.lut_rw_addresses:
                addresses_and_luts.append(lut_rw_address)
            for lut_ro_address in self.lut_ro_addresses:
                addresses_and_luts.append(lut_ro_address)

        for (
            program_index,
            instruction_id,
            accounts,
            instruction_data,
        ) in raw_instructions:
            program_id = base58.encode(self.addresses[program_index][0])
            instruction_accounts = [
                addresses_and_luts[account_index] for account_index in accounts
            ]
            instruction = get_instruction(
                program_id,
                instruction_id,
                instruction_accounts,
                instruction_data,
            )
            self.instructions.append(instruction)

        assert serialized_tx.remaining_count() == 0
