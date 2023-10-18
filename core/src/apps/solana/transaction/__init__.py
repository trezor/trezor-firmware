from typing import TYPE_CHECKING

from trezor.crypto import base58
from trezor.utils import BufferReader
from trezor.wire import ProcessError

from .instruction import Instruction
from .instructions import get_instruction, get_instruction_id_length
from .parse import (
    parse_address_lookup_tables,
    parse_addresses,
    parse_block_hash,
    parse_header,
    parse_instructions,
)

if TYPE_CHECKING:
    from ..types import Account, Address, AddressReference, RawInstruction


class Transaction:
    blind_signing = False
    required_signers_count = 0

    is_legacy: bool
    version: int

    addresses: list[Address]

    blockhash: bytes

    raw_instructions: list[RawInstruction]
    instructions: list[Instruction] = []

    address_lookup_tables_rw_addresses: list[AddressReference] = []
    address_lookup_tables_ro_addresses: list[AddressReference] = []

    def __init__(self, serialized_tx: BufferReader) -> None:
        self._parse_transaction(serialized_tx)
        self._create_instructions()
        self._determine_if_blind_signing()

    def _parse_transaction(self, serialized_tx):
        (
            self.is_legacy,
            self.version,
            num_required_signatures,
            num_signature_read_only_addresses,
            num_read_only_addresses,
        ) = parse_header(serialized_tx)

        self.required_signers_count = num_required_signatures

        self.addresses = parse_addresses(
            serialized_tx,
            num_required_signatures,
            num_signature_read_only_addresses,
            num_read_only_addresses,
        )

        self.blockhash = parse_block_hash(serialized_tx)

        self.raw_instructions = parse_instructions(
            self.addresses, get_instruction_id_length, serialized_tx
        )

        if not self.is_legacy:
            (
                self.address_lookup_tables_rw_addresses,
                self.address_lookup_tables_ro_addresses,
            ) = parse_address_lookup_tables(serialized_tx)

        if serialized_tx.remaining_count() != 0:
            raise ProcessError("Invalid transaction")

    def _get_combined_accounts(self):
        """
        Combine accounts from transaction's accounts field with accounts from address lookup tables.
        Instructions reference accounts by index in this combined list.
        """
        accounts: list[Account] = []
        for address in self.addresses:
            accounts.append(address)

        for rw_address in self.address_lookup_tables_rw_addresses:
            accounts.append(rw_address)
        for ro_address in self.address_lookup_tables_ro_addresses:
            accounts.append(ro_address)

        return accounts

    def _create_instructions(self):
        combined_accounts = self._get_combined_accounts()

        for (
            program_index,
            instruction_id,
            accounts,
            instruction_data,
        ) in self.raw_instructions:
            program_id = base58.encode(self.addresses[program_index][0])
            instruction_accounts = [
                combined_accounts[account_index] for account_index in accounts
            ]
            instruction = get_instruction(
                program_id,
                instruction_id,
                instruction_accounts,
                instruction_data,
            )

            self.instructions.append(instruction)

    def _determine_if_blind_signing(self):
        for instruction in self.instructions:
            if (
                not instruction.is_program_supported
                or not instruction.is_instruction_supported
            ):
                self.blind_signing = True
                break
