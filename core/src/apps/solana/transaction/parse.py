from typing import TYPE_CHECKING

from trezor.crypto import base58
from apps.common.readers import read_uint32_le, read_uint64_le, read_compact_size

from ..constants import (
    ADDRESS_READ_ONLY,
    ADDRESS_RW,
    ADDRESS_SIG,
    ADDRESS_SIG_READ_ONLY,
    ADDRESS_SIZE,
)

if TYPE_CHECKING:
    from typing import Callable

    from trezor.utils import BufferReader

    from ..types import Address, AddressReference, InstructionIdFormat


def parseHeader(serialized_tx: BufferReader) -> tuple[bool, int, int, int, int]:
    assert serialized_tx.remaining_count() > 3

    isLegacy: bool = True
    version: int = 0

    if serialized_tx.peek() & 0b10000000:
        isLegacy = False
        version = serialized_tx.get() & 0b01111111
        # only version 0 is supported
        # less or equal is used in order to support future versions
        assert version <= 0
    num_required_signatures: int = serialized_tx.get()
    num_signature_read_only_addresses: int = serialized_tx.get()
    num_read_only_addresses: int = serialized_tx.get()

    return (
        isLegacy,
        version,
        num_required_signatures,
        num_signature_read_only_addresses,
        num_read_only_addresses,
    )

def parseAddresses(
    serialized_tx: BufferReader,
    num_required_signatures: int,
    num_signature_read_only_addresses: int,
    num_read_only_addresses: int,
) -> list[Address]:
    num_of_addresses = read_compact_size(serialized_tx)

    assert (
        num_of_addresses
        >= num_required_signatures
        + num_signature_read_only_addresses
        + num_read_only_addresses
    )

    addresses: list[Address] = []
    for i in range(num_of_addresses):
        assert ADDRESS_SIZE <= serialized_tx.remaining_count()

        if i < num_required_signatures:
            type = ADDRESS_SIG
        elif i < num_required_signatures + num_signature_read_only_addresses:
            type = ADDRESS_SIG_READ_ONLY
        elif (
            i
            < num_required_signatures
            + num_signature_read_only_addresses
            + num_read_only_addresses
        ):
            type = ADDRESS_RW
        else:
            type = ADDRESS_READ_ONLY

        address = parsePubkey(serialized_tx)

        addresses.append((address, type))

    return addresses


# data = r.read_memoryview(4)
# return int.from_bytes(data, "little")

def parseBlockHash(serialized_tx: BufferReader) -> bytes:
    assert serialized_tx.remaining_count() >= 32
    return bytes(serialized_tx.read_memoryview(32))


def parseInstructions(
    addresses: list[Address],
    get_instruction_id_format: Callable[[str], InstructionIdFormat],
    serialized_tx: BufferReader,
    # [program_index, instruction_id, accounts, instruction_data]
) -> list[tuple[int, int, list[int], bytes]]:
    num_of_instructions = read_compact_size(serialized_tx)

    instructions: list[tuple[int, int, list[int], bytes]] = []

    for _ in range(num_of_instructions):
        program_index = serialized_tx.get()
        program_id = base58.encode(addresses[program_index][0])
        num_of_accounts = read_compact_size(serialized_tx)
        accounts: list[int] = []
        for _ in range(num_of_accounts):
            assert serialized_tx.remaining_count() > 0
            account_index = serialized_tx.get()
            accounts.append(account_index)

        data_length = read_compact_size(serialized_tx)

        instruction_id_format = get_instruction_id_format(program_id)
        instruction_id_length = instruction_id_format["length"]
        # some programs e.g. Associated Token Account Program don't include the instruction
        # id in the data for instruction id 0 but they include for the other instructions.
        if data_length < instruction_id_length:
            if instruction_id_format["is_included_if_zero"]:
                raise ValueError("Invalid instruction data")

            instruction_id = 0
        else:
            instruction_id = int.from_bytes(
                serialized_tx.read_memoryview(instruction_id_length), "little"
            )

        instruction_data = serialized_tx.read_memoryview(data_length - instruction_id_length)

        instructions.append((program_index, instruction_id, accounts, instruction_data))

    return instructions


def parsePubkey(serialized_tx: BufferReader) -> bytes:
    assert serialized_tx.remaining_count() >= 32
    return bytes(serialized_tx.read_memoryview(32))


def parseEnum(serialized_tx: BufferReader) -> int:
    assert serialized_tx.remaining_count() >= 1
    return serialized_tx.get()


def parseString(serialized_tx: BufferReader) -> str:
    # TODO SOL: validation shall be checked (length is less than 2^32 or even less)
    length = read_uint64_le(serialized_tx)
    assert serialized_tx.remaining_count() >= length
    return bytes(serialized_tx.read_memoryview(length)).decode("utf-8")


def parseMemo(serialized_tx: BufferReader) -> str:
    return bytes(serialized_tx.read_memoryview(serialized_tx.remaining_count())).decode("utf-8")


def parseProperty(reader: BufferReader, type: str) -> str | int | bytes:
    if type == "u8":
        return reader.get()
    elif type == "u32":
        return read_uint32_le(reader)
    elif type == "u64":
        return read_uint64_le(reader)
    elif type == "i32":
        return read_uint32_le(reader)
    elif type == "i64":
        return read_uint64_le(reader)
    elif type in ("pubkey", "authority"):
        return parsePubkey(reader)
    elif type == "enum":
        return parseEnum(reader)
    elif type == "string":
        return parseString(reader)
    elif type == "memo":
        return parseMemo(reader)
    else:
        return parseEnum(reader)
        # raise NotImplementedError


def parseLut(
    serialized_tx: BufferReader,
) -> tuple[list[AddressReference], list[AddressReference]]:
    address_table_lookup_rw_addresses = []
    address_table_lookup_ro_addresses = []

    address_table_lookups_count = read_compact_size(serialized_tx)
    for _ in range(address_table_lookups_count):
        account = parsePubkey(serialized_tx)

        table_rw_indexes_count = read_compact_size(serialized_tx)
        for _ in range(table_rw_indexes_count):
            address_table_lookup_rw_addresses.append(
                (account, serialized_tx.get(), ADDRESS_RW)
            )

        table_ro_indexes_count = read_compact_size(serialized_tx)
        for _ in range(table_ro_indexes_count):
            address_table_lookup_ro_addresses.append(
                (account, serialized_tx.get(), ADDRESS_READ_ONLY)
            )

    return address_table_lookup_rw_addresses, address_table_lookup_ro_addresses
