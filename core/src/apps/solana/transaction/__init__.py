from typing import TYPE_CHECKING

from trezor.crypto import base58
from trezor.utils import BufferReader
from trezor.wire import DataError

from ..types import AddressType
from .instruction import Instruction
from .instructions import get_instruction, get_instruction_id_length
from .parse import parse_block_hash, parse_pubkey, parse_var_int

if TYPE_CHECKING:
    from ..types import Account, Address, AddressReference, RawInstruction


class Transaction:
    blind_signing = False
    required_signers_count = 0

    version: int | None = None

    addresses: list[Address]

    blockhash: bytes

    raw_instructions: list[RawInstruction]
    instructions: list[Instruction]

    address_lookup_tables_rw_addresses: list[AddressReference]
    address_lookup_tables_ro_addresses: list[AddressReference]

    def __init__(self, serialized_tx: bytes) -> None:
        self._parse_transaction(serialized_tx)
        self._create_instructions()
        self._determine_if_blind_signing()

    def _parse_transaction(self, serialized_tx: bytes) -> None:
        serialized_tx_reader = BufferReader(serialized_tx)
        self._parse_header(serialized_tx_reader)

        self._parse_addresses(serialized_tx_reader)

        self.blockhash = parse_block_hash(serialized_tx_reader)

        self._parse_instructions(serialized_tx_reader)

        self._parse_address_lookup_tables(serialized_tx_reader)

        if serialized_tx_reader.remaining_count() != 0:
            raise DataError("Invalid transaction")

    def _parse_header(self, serialized_tx_reader: BufferReader) -> None:
        self.version: int | None = None

        if serialized_tx_reader.peek() & 0b10000000:
            self.version = serialized_tx_reader.get() & 0b01111111
            # only version 0 is supported
            if self.version > 0:
                raise DataError("Unsupported transaction version")

        self.required_signers_count: int = serialized_tx_reader.get()
        self.num_signature_read_only_addresses: int = serialized_tx_reader.get()
        self.num_read_only_addresses: int = serialized_tx_reader.get()

    def _parse_addresses(self, serialized_tx_reader: BufferReader) -> None:
        num_of_addresses = parse_var_int(serialized_tx_reader)

        assert (
            num_of_addresses
            >= self.required_signers_count
            + self.num_signature_read_only_addresses
            + self.num_read_only_addresses
        )

        addresses: list[Address] = []
        for i in range(num_of_addresses):
            if i < self.required_signers_count:
                type = AddressType.AddressSig
            elif (
                i < self.required_signers_count + self.num_signature_read_only_addresses
            ):
                type = AddressType.AddressSigReadOnly
            elif (
                i
                < self.required_signers_count
                + self.num_signature_read_only_addresses
                + self.num_read_only_addresses
            ):
                type = AddressType.AddressRw
            else:
                type = AddressType.AddressReadOnly

            address = parse_pubkey(serialized_tx_reader)

            addresses.append((address, type))

        self.addresses = addresses

    def _parse_instructions(self, serialized_tx_reader: BufferReader) -> None:
        num_of_instructions = parse_var_int(serialized_tx_reader)

        self.raw_instructions = []

        for _ in range(num_of_instructions):
            program_index = serialized_tx_reader.get()
            program_id = base58.encode(self.addresses[program_index][0])
            num_of_accounts = parse_var_int(serialized_tx_reader)
            accounts: list[int] = []
            for _ in range(num_of_accounts):
                account_index = serialized_tx_reader.get()
                accounts.append(account_index)

            data_length = parse_var_int(serialized_tx_reader)

            instruction_id_length = get_instruction_id_length(program_id)
            if 0 < instruction_id_length <= data_length:
                instruction_id = int.from_bytes(
                    serialized_tx_reader.read_memoryview(instruction_id_length),
                    "little",
                )
            else:
                instruction_id = None

            instruction_data = serialized_tx_reader.read_memoryview(
                max(0, data_length - instruction_id_length)
            )

            self.raw_instructions.append(
                (program_index, instruction_id, accounts, instruction_data)
            )

    def _parse_address_lookup_tables(self, serialized_tx: BufferReader) -> None:
        self.address_lookup_tables_rw_addresses = []
        self.address_lookup_tables_ro_addresses = []

        if self.version is None:
            return

        address_lookup_tables_count = parse_var_int(serialized_tx)
        for _ in range(address_lookup_tables_count):
            account = parse_pubkey(serialized_tx)

            table_rw_indexes_count = parse_var_int(serialized_tx)
            for _ in range(table_rw_indexes_count):
                index = serialized_tx.get()
                self.address_lookup_tables_rw_addresses.append(
                    (account, index, AddressType.AddressRw)
                )

            table_ro_indexes_count = parse_var_int(serialized_tx)
            for _ in range(table_ro_indexes_count):
                index = serialized_tx.get()
                self.address_lookup_tables_ro_addresses.append(
                    (account, index, AddressType.AddressReadOnly)
                )

    def _get_combined_accounts(self) -> list[Account]:
        accounts: list[Account] = []
        for address in self.addresses:
            accounts.append(address)

        for rw_address in self.address_lookup_tables_rw_addresses:
            accounts.append(rw_address)
        for ro_address in self.address_lookup_tables_ro_addresses:
            accounts.append(ro_address)

        return accounts

    def _create_instructions(self) -> None:
        # Instructions reference accounts by index in this combined list.
        combined_accounts = (
            self.addresses  # type: ignore [Operator "+" not supported for types "list[Address]" and "list[AddressReference]"]
            + self.address_lookup_tables_rw_addresses
            + self.address_lookup_tables_ro_addresses
        )

        self.instructions = []
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

    def _determine_if_blind_signing(self) -> None:
        for instruction in self.instructions:
            if (
                not instruction.is_program_supported
                or not instruction.is_instruction_supported
            ):
                self.blind_signing = True
                break
