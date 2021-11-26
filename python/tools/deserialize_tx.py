#!/usr/bin/env python3

# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
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

import os
import sys
from typing import Any, Optional

try:
    import construct as c
    from construct import len_, this
except ImportError:
    sys.stderr.write(
        "This tool requires Construct. Install it with 'pip install Construct'.\n"
    )
    sys.exit(1)


if os.isatty(sys.stdin.fileno()):
    tx_hex = input("Enter transaction in hex format: ")
else:
    tx_hex = sys.stdin.read().strip()

tx_bin = bytes.fromhex(tx_hex)


CompactUintStruct = c.Struct(
    "base" / c.Int8ul,
    "ext" / c.Switch(this.base, {0xFD: c.Int16ul, 0xFE: c.Int32ul, 0xFF: c.Int64ul}),
)


class CompactUintAdapter(c.Adapter):
    def _encode(self, obj: int, context: Any, path: Any) -> dict:
        if obj < 0xFD:
            return {"base": obj}
        if obj < 2 ** 16:
            return {"base": 0xFD, "ext": obj}
        if obj < 2 ** 32:
            return {"base": 0xFE, "ext": obj}
        if obj < 2 ** 64:
            return {"base": 0xFF, "ext": obj}
        raise ValueError("Value too big for compact uint")

    def _decode(self, obj: dict, context: Any, path: Any):
        return obj["ext"] or obj["base"]


class ConstFlag(c.Adapter):
    def __init__(self, const: bytes) -> None:
        self.const = const
        super().__init__(c.Optional(c.Const(const)))

    def _encode(self, obj: Any, context: Any, path: Any) -> Optional[bytes]:
        return self.const if obj else None

    def _decode(self, obj: Any, context: Any, path: Any) -> bool:
        return obj is not None


CompactUint = CompactUintAdapter(CompactUintStruct)

TxInput = c.Struct(
    "tx" / c.Bytes(32),
    "index" / c.Int32ul,
    # TODO coinbase tx
    "script" / c.Prefixed(CompactUint, c.GreedyBytes),
    "sequence" / c.Int32ul,
)

TxOutput = c.Struct(
    "value" / c.Int64ul,
    "pk_script" / c.Prefixed(CompactUint, c.GreedyBytes),
)

StackItem = c.Prefixed(CompactUint, c.GreedyBytes)
TxInputWitness = c.PrefixedArray(CompactUint, StackItem)

Transaction = c.Struct(
    "version" / c.Int32ul,
    "segwit" / ConstFlag(b"\x00\x01"),
    "inputs" / c.PrefixedArray(CompactUint, TxInput),
    "outputs" / c.PrefixedArray(CompactUint, TxOutput),
    "witness" / c.If(this.segwit, TxInputWitness[len_(this.inputs)]),
    "lock_time" / c.Int32ul,
    c.Terminated,
)

print(Transaction.parse(tx_bin))
