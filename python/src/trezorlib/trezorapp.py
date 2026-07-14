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

from hashlib import sha256
from typing import TYPE_CHECKING, Any, Optional, Tuple, cast

import construct as c

from . import messages
from .construct_helpers import TupleAdapter

if TYPE_CHECKING:
    from .transport.session import Session


class AppHeader:
    # Magic number to identify the app binary format
    magic: int
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
    target_architecture: int
    # Size of binary payload in bytes (code + init and relocation data)
    code_size: int
    # Size of RAM required by the app (includes stack, heap, and static data)
    data_size: int
    # Hash of the first payload chunk
    chunk_hash: bytes
    # Size of each chunk of the binary payload
    chunk_size: int
    if TYPE_CHECKING:
        # construct DSL uses overloaded operators that Pylance cannot type-check well.
        SUBCON: Any
    else:
        # fmt: off
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
            "payload_type" / c.Int8ul,
            "_reserved1" / c.Padding(2),
            "code_size" / c.Int32ul,
            "data_size" / c.Int32ul,
            "chunk_hash" / c.Bytes(32),
            "chunk_size" / c.Int16ul,
            "_reserved2" / c.Padding(2),
            "_end_offset" / c.Tell,
            c.Padding(
                lambda this: this.header_size - (this._end_offset - this._start_offset)
            ),
        )
        # fmt: on

    @classmethod
    def parse(cls, data: bytes) -> "AppHeader":
        return cast(AppHeader, cls.SUBCON.parse(data))


class AppImage:
    # Parsed fixed-size app header
    header: AppHeader
    # Original header bytes including padding
    header_bytes: bytes
    # Image payload (elf file, or other proprietary binary format)
    payload: bytes

    if TYPE_CHECKING:
        # construct DSL uses overloaded operators that Pylance cannot type-check well.
        SUBCON: Any
    else:
        SUBCON = c.Struct(
            "_header_raw" / c.RawCopy(AppHeader.SUBCON),
            "header" / c.Computed(lambda this: this._header_raw.value),
            "header_bytes" / c.Computed(lambda this: this._header_raw.data),
            "payload" / c.GreedyBytes,
        )

    @classmethod
    def parse(cls, data: bytes) -> "AppImage":
        container = cls.SUBCON.parse(data)
        obj = object.__new__(cls)
        obj.header = container.header
        obj.header_bytes = container.header_bytes
        obj.payload = container.payload
        return obj

    def header_hash(self) -> bytes:
        """Calculate the SHA256 hash of the application header."""
        return sha256(self.header_bytes).digest()

    def chunks(self) -> list[tuple[bytes, bytes]]:
        """Split the payload into chunks and calculate the hash chain."""
        size = self.header.chunk_size
        chunks = [self.payload[i : i + size] for i in range(0, len(self.payload), size)]

        result = []
        hash = b"\x00" * 32

        for chunk in reversed(chunks):
            result.append((chunk, hash))
            hash = sha256(chunk + hash).digest()

        if hash != self.header.chunk_hash:
            raise ValueError("Calculated payload hash does not match header")

        return list(reversed(result))


def _format_version(version: tuple[int, ...]) -> str:
    """Format a version tuple into a string representation, removing trailing zeros."""
    parts = list(version)
    while len(parts) > 2 and parts[-1] == 0:
        parts.pop()
    return "v" + ".".join(str(part) for part in parts)


def load(
    session: "Session",
    binary: bytes,
    proof: bytes,
    min_version: Optional[Tuple[int, int, int, int]],
    force_reload: bool = False,
) -> int:
    """Load an external application onto the device.

    Returns:
        Instance ID of the loaded app
    """

    image = AppImage.parse(binary)

    if min_version is not None:
        min_version_info = f"{_format_version(min_version)}+"
        if image.header.version < min_version:
            raise ValueError(
                "Application version "
                f"{_format_version(image.header.version)} "
                "is less than the minimum required version "
                f"{_format_version(min_version)}"
            )
    else:
        min_version_info = ""
        min_version = image.header.version

    print(f"Requesting {image.header.id} {min_version_info}")

    header_hash = image.header_hash() if force_reload else b""

    # Send a request to the device to load the app, providing the hash, app ID, and minimum version.
    resp = session.call(
        messages.TrezorAppLoad(
            hash=header_hash, id=image.header.id, version=min_version
        )
    )

    # If the device requests the binary, we proceed to upload it.
    if isinstance(resp, messages.TrezorAppHeaderRequest):
        # Send the header and proof to the device
        resp = session.call(
            messages.TrezorAppHeaderAck(header=image.header_bytes, proof=proof)
        )

        chunks = image.chunks()

        print(
            f"Uploading {image.header.id} {_format_version(image.header.version)} ({len(image.payload) / 1024:.1f} KB)"
        )
        # Send the payload in chunks as requested by the device
        while isinstance(resp, messages.TrezorAppDataChunkRequest):
            chunk = chunks[resp.index]
            resp = session.call(
                messages.TrezorAppDataChunkAck(data=chunk[0], hash=chunk[1])
            )

    # After the upload, the device should respond with TrezorAppLoaded containing the instance ID.
    resp = messages.TrezorAppLoaded.ensure_isinstance(resp)
    return resp.instance_id
