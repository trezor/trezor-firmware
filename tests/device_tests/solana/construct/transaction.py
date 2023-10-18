from construct import GreedyBytes, If, Int8ul, Struct, this

from .custom_constructs import CompactArray, PublicKey, Version

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

Message = Struct(
    "version" / Version,
    "header" / Header,
    "accounts" / Accounts,
    "blockhash" / PublicKey,
    "instructions" / CompactArray(GreedyBytes),
    "luts" / If(this.version != "legacy", Luts),
)
