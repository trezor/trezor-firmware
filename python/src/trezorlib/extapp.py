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

from __future__ import annotations

from hashlib import sha256
from typing import cast

import construct as c
from construct_classes import subcon

from .construct_helpers import Reserved, TupleAdapter
from .firmware.sanity_struct import SanityCheckedStruct


class AppHeader(SanityCheckedStruct):
    # Magic number to identify the app binary format
    magic: bytes
    # Header size in bytes
    header_size: int
    # Unique identifier of the app
    id: str
    # Application name
    name: str
    # Vendor name
    vendor: str
    # Target model
    model: str
    # App version in the format major.minor.patch.build, each as a byte
    version: tuple[int, int, int, int]
    # SDK version that the app was built against
    sdk_version: tuple[int, int, int, int]
    # ABI version that the app was built against
    abi_version: int
    # Target architecture of the binary payload (e.g., ARMV8M, X86_64)
    target_arch: int
    # Application privilege ring
    app_ring: int
    # Application language
    language: int
    # Size of binary payload in bytes (code + init and relocation data)
    code_size: int
    # Size of RAM required by the app (includes stack, heap, and static data)
    data_size: int
    # Hash of the first payload chunk
    chunk_hash: bytes
    # Size of each chunk of the binary payload
    chunk_size: int
    # Reserved for future use
    reserved_2: bytes
    # Curves used for the app (e.g., secp256k1, ed25519)
    curves: list[str]
    # Allowed BIP32 path prefixes
    paths: list[str]
    # Size in bytes of the IPC inbox Core registers for the app at launch
    ipc_buffer_size: int
    # Reserved for future use
    reserved_3: bytes

    SUBCON = c.Struct(
        "_start_offset" / c.Tell,
        "magic" / c.Const(b"TRZA"),
        "header_size" / c.Int32ul,
        "id" / c.PaddedString(32, "utf-8"),
        "name" / c.PaddedString(32, "utf-8"),
        "vendor" / c.PaddedString(32, "utf-8"),
        "model" / c.PaddedString(4, "utf-8"),
        "version" / TupleAdapter(c.Int8ul, c.Int8ul, c.Int8ul, c.Int8ul),
        "sdk_version" / TupleAdapter(c.Int8ul, c.Int8ul, c.Int8ul, c.Int8ul),
        "abi_version" / c.Int8ul,
        "target_arch" / c.Int8ul,
        "app_ring" / c.Int8ul,
        "language" / c.Int8ul,
        "code_size" / c.Int32ul,
        "data_size" / c.Int32ul,
        "chunk_hash" / c.Bytes(32),
        "chunk_size" / c.Int16ul,
        "reserved_2" / Reserved(2),
        "curves"
        / c.ExprAdapter(
            c.Bytes(64),
            decoder=lambda obj, ctx: [
                curve.decode("utf-8")
                for curve in cast(bytes, obj).split(b"\0")
                if curve
            ],
            encoder=lambda obj, ctx: b"\0".join(
                curve.encode("utf-8") for curve in cast(list[str], obj)
            ).ljust(64, b"\0"),
        ),
        "paths"
        / c.ExprAdapter(
            c.Bytes(256),
            decoder=lambda obj, ctx: [
                path.decode("utf-8") for path in cast(bytes, obj).split(b"\0") if path
            ],
            encoder=lambda obj, ctx: b"\0".join(
                path.encode("utf-8") for path in cast(list[str], obj)
            ).ljust(256, b"\0"),
        ),
        "ipc_buffer_size" / c.Int32ul,
        "_end_offset" / c.Tell,
        "reserved_3"
        / Reserved(c.this.header_size - c.this._end_offset + c.this._start_offset),
    )

    def fingerprint(self) -> bytes:
        return sha256(self.build()).digest()


class AppImage(SanityCheckedStruct):
    # Parsed fixed-size app header
    header: AppHeader = subcon(AppHeader)
    # Image payload (elf file, or other proprietary binary format)
    payload: bytes

    SUBCON = c.Struct(
        "header" / AppHeader.SUBCON,
        "payload" / c.GreedyBytes,
    )

    def header_bytes(self) -> bytes:
        """Rebuild the original header bytes including padding."""
        return self.header.build()

    def fingerprint(self) -> bytes:
        """Calculate the SHA256 hash of the application header."""
        return self.header.fingerprint()

    def chunks(self) -> list[tuple[bytes, bytes]]:
        """Split the payload into chunks and calculate the hash chain."""
        size = self.header.chunk_size
        chunks = [self.payload[i : i + size] for i in range(0, len(self.payload), size)]

        result = []
        hash = b"\x00" * 32

        for chunk in reversed(chunks):
            result.append((chunk, hash))
            hash = sha256(hash + chunk).digest()

        if hash != self.header.chunk_hash:
            raise ValueError("Calculated payload hash does not match header")

        return list(reversed(result))
