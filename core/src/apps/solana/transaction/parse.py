from typing import TYPE_CHECKING
from trezor.crypto import base58
from ..constants import (
    ADDRESS_READ_ONLY,
    ADDRESS_RW,
    ADDRESS_SIG,
    ADDRESS_SIG_READ_ONLY,
    ADDRESS_SIZE,
)

if TYPE_CHECKING:
    from trezor.utils import BufferReader
    from ..types import Address, AddressReference, RawInstruction

def parseHeader(serialized_tx: BufferReader) -> tuple[bool, int, int, int, int]:
    assert serialized_tx.remaining_count() > 3

    isLegacy: bool = True
    version: int = 0
    
    if serialized_tx.peek() & 0b10000000:
        isLegacy = False
        version = serialized_tx.get() & 0b01111111
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

def parseVarInt(serialized_tx: BufferReader) -> int:
    value = 0
    shift = 0
    while(serialized_tx.remaining_count()):
        B = serialized_tx.get()
        value += (B & 0b01111111) << shift
        shift += 7
        if B & 0b10000000 == 0:
            return value
        
    raise BufferError

def parseAddresses(
        serialized_tx: BufferReader,
        num_required_signatures: int,
        num_signature_read_only_addresses: int,
        num_read_only_addresses: int
    ) -> list[Address]:
    num_of_addresses = parseVarInt(serialized_tx)

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
        
        address = serialized_tx.read(ADDRESS_SIZE)

        addresses.append((base58.encode(address), type))

    return addresses

def parseBlockHash(
        serialized_tx: BufferReader
    ) -> bytes:
    assert serialized_tx.remaining_count() >= 32
    return serialized_tx.read(32)

def parseInstructions(
        serialized_tx: BufferReader
        # [program_index, instruction_id, accounts, instruction_data]
    ) -> list[tuple[int, int, list[int], bytes]]:

    num_of_instructions = parseVarInt(serialized_tx)

    instructions: list[tuple[int, int, list[int], bytes]] = []

    for _ in range(num_of_instructions):
        program_index = serialized_tx.get()
        num_of_accounts = parseVarInt(serialized_tx)
        accounts: list[int] = []
        for _ in range(num_of_accounts):
            assert serialized_tx.remaining_count() > 0
            account_index = serialized_tx.get()
            accounts.append(account_index)
        data_length = parseVarInt(serialized_tx)
        assert data_length >= 4
        instruction_id: int = int.from_bytes(serialized_tx.read(4), "little")
        instruction_data: bytes = serialized_tx.read(data_length - 4)

        instructions.append((program_index, instruction_id, accounts, instruction_data))
    
    return instructions

def parseU32(serialized_tx: BufferReader) -> int:
    assert serialized_tx.remaining_count() >= 4
    return int.from_bytes(serialized_tx.read(4), "little")

def parseU64(serialized_tx: BufferReader) -> int:
    assert serialized_tx.remaining_count() >= 8
    return int.from_bytes(serialized_tx.read(8), "little")

def parseI32(serialized_tx: BufferReader) -> int:
    assert serialized_tx.remaining_count() >= 4
    return int.from_bytes(serialized_tx.read(4), "little")

def parseI64(serialized_tx: BufferReader) -> int:
    assert serialized_tx.remaining_count() >= 8
    return int.from_bytes(serialized_tx.read(8), "little")

def parsePubkey(serialized_tx: BufferReader) -> bytes:
    assert serialized_tx.remaining_count() >= 32
    return serialized_tx.read(32)

def parseEnum(serialized_tx: BufferReader) -> int:
    assert serialized_tx.remaining_count() >= 1
    return serialized_tx.get()

def parseString(serialized_tx: BufferReader) -> str:
    length = parseU64(serialized_tx)
    assert serialized_tx.remaining_count() >= length
    return serialized_tx.read(length).decode("utf-8")

def parseProperty(serialized_tx: BufferReader, template: dict) -> str | int | bytes:
    if template["type"] == "u32":
        return parseU32(serialized_tx)
    elif template["type"] == "u64":
        return parseU64(serialized_tx)
    elif template["type"] == "i32":
        return parseI32(serialized_tx)
    elif template["type"] == "i64":
        return parseI64(serialized_tx)
    elif template["type"] == "pubkey":
        return parsePubkey(serialized_tx)
    elif template["type"] == "enum":
        return parseEnum(serialized_tx)
    elif template["type"] == "string":
        return parseString(serialized_tx)
    else:
        return parseEnum(serialized_tx)
        # raise NotImplementedError

def parseLut(serialized_tx: BufferReader) -> any:
    address_table_lookup_rw_addresses = []
    address_table_lookup_ro_addresses = []

    address_table_lookups_count = parseVarInt(serialized_tx)
    for _ in range(address_table_lookups_count):
        account = base58.encode(serialized_tx.read(ADDRESS_SIZE))

        table_rw_indexes_count = parseVarInt(serialized_tx)
        for _ in range(table_rw_indexes_count):
            address_table_lookup_rw_addresses.append(
                (account, serialized_tx.get(), ADDRESS_RW)
            )

        table_ro_indexes_count = parseVarInt(serialized_tx)
        for _ in range(table_ro_indexes_count):
            address_table_lookup_ro_addresses.append(
                (account, serialized_tx.get(), ADDRESS_READ_ONLY)
            )

    return address_table_lookup_rw_addresses, address_table_lookup_ro_addresses
    