#!/usr/bin/env python3

import os
import sys

try:
    import construct as c
except ImportError:
    sys.stderr.write("This tool requires Construct. Install it with 'pip install Construct'.\n")
    sys.exit(1)

from construct import this, len_

if os.isatty(sys.stdin.fileno()):
    tx_hex = input("Enter transaction in hex format: ")
else:
    tx_hex = sys.stdin.read().strip()

tx_bin = bytes.fromhex(tx_hex)


CompactUintStruct = c.Struct(
    "base" / c.Int8ul,
    "ext" / c.Switch(this.base, {0xfd: c.Int16ul, 0xfe: c.Int32ul, 0xff: c.Int64ul}),
)


class CompactUintAdapter(c.Adapter):
    def _encode(self, obj, context, path):
        if obj < 0xfd:
            return {"base": obj}
        if obj < 2 ** 16:
            return {"base": 0xfd, "ext": obj}
        if obj < 2 ** 32:
            return {"base": 0xfe, "ext": obj}
        if obj < 2 ** 64:
            return {"base": 0xff, "ext": obj}
        raise ValueError("Value too big for compact uint")

    def _decode(self, obj, context, path):
        return obj["ext"] or obj["base"]


class ConstFlag(c.Adapter):
    def __init__(self, const):
        self.const = const
        super().__init__(c.Optional(c.Const(const)))

    def _encode(self, obj, context, path):
        return self.const if obj else None

    def _decode(self, obj, context, path):
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
