# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

from construct import (
    Byte,
    GreedyBytes,
    If,
    Int8ul,
    Int16ul,
    Int32ul,
    Int64ul,
    Prefixed,
    RawCopy,
    Struct,
    this,
)

from .custom_constructs import CompactArray, CompactU16, PublicKey, Version

Header = Struct(
    "signers" / Int8ul,
    "readonly_signers" / Int8ul,
    "readonly_non_signers" / Int8ul,
)

Accounts = CompactArray(PublicKey)


Lut = Struct(
    "account" / PublicKey,
    "readwrite" / CompactArray(Int8ul),
    "readonly" / CompactArray(Int8ul),
)

Luts = CompactArray(Lut)

RawInstruction = RawCopy(
    Struct(
        "program_id" / Byte,
        "accounts" / CompactArray(Byte),
        "data" / Prefixed(CompactU16, GreedyBytes),
    )
)

Message = Struct(
    "version" / Version,
    "header" / Header,
    "accounts" / Accounts,
    "blockhash" / PublicKey,
    "instructions" / CompactArray(RawInstruction),
    "luts" / If(this.version != None, Luts),  # noqa: E711
)

# v1 transactions, see SIMD-0385. All their instruction headers precede all
# the instruction payloads, which a plain function serializes more readably
# than a construct.

# Name, mask bits, and construct of each config value, in the order of the bits.
CONFIG_FIELDS = (
    ("priority_fee", 0b0_0011, Int64ul),
    ("compute_unit_limit", 0b0_0100, Int32ul),
    ("loaded_accounts_data_size_limit", 0b0_1000, Int32ul),
    ("heap_size", 0b1_0000, Int32ul),
)


def _serialize_config(config) -> tuple[int, bytearray]:
    """Return the config mask and the serialized config values."""
    config = config or {}
    config_mask = 0
    config_values = bytearray()
    for name, bits, value_construct in CONFIG_FIELDS:
        if config.get(name) is not None:
            config_mask |= bits
            config_values += value_construct.build(config[name])
    return config_mask, config_values


def serialize_v1_tx(header, accounts, blockhash, instructions, config=None) -> bytes:
    """Serialize a v1 transaction without its signatures.

    `instructions` are parsed `RawInstruction` values. `config` maps the names
    in CONFIG_FIELDS to their values, missing values are not set.
    """
    config_mask, config_values = _serialize_config(config)

    buf = bytearray()

    buf += Version.build(1)
    buf += Header.build(header)
    buf += Int32ul.build(config_mask)
    buf += PublicKey.build(blockhash)
    buf += Int8ul.build(len(instructions))
    buf += Int8ul.build(len(accounts))

    for account in accounts:
        buf += PublicKey.build(account)

    buf += config_values

    for instruction in instructions:
        buf += Int8ul.build(instruction.program_id)
        buf += Int8ul.build(len(instruction.accounts))
        buf += Int16ul.build(len(instruction.data))
    for instruction in instructions:
        buf += bytes(instruction.accounts)
        buf += instruction.data
    return bytes(buf)
