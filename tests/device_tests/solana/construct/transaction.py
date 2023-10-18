from construct import Byte, GreedyBytes, If, Int8ul, Prefixed, RawCopy, Struct, this

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
