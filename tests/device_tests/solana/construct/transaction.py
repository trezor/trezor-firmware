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
