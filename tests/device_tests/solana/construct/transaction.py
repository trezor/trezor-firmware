from construct import If, Int8ul, Struct, this

from .custom_constructs import CompactArray, PublicKey, Version
from .instructions import _INSTRUCTION

_HEADER = Struct(
    "signers" / Int8ul,
    "readonly_signers" / Int8ul,
    "readonly_non_signers" / Int8ul,
)

_ACCOUNTS = CompactArray(PublicKey())


_LUT = Struct(
    "account" / PublicKey(),
    "readwrite" / CompactArray(Int8ul),
    "readonly" / CompactArray(Int8ul),
)

_LUTS = CompactArray(_LUT)

MESSAGE = Struct(
    "version" / Version(),
    "header" / _HEADER,
    "accounts" / _ACCOUNTS,
    "blockhash" / PublicKey(),
    "instructions" / CompactArray(_INSTRUCTION),
    "luts" / If(this.version != "legacy", _LUTS),
)
