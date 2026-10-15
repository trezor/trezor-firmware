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

import base64
import json
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, Optional, cast

import construct as c
from construct_classes import subcon

from . import messages
from .construct_helpers import Reserved, TupleAdapter
from .firmware.sanity_struct import SanityCheckedStruct
from .root_packet import RootPacket

if TYPE_CHECKING:
    from .client import Session


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
    reserved_2: bytes | None = None
    # Curves used for the app (e.g., secp256k1, ed25519)
    curves: list[str]
    # Allowed BIP32 path prefixes
    paths: list[str]
    # Size in bytes of the IPC inbox Core registers for the app at launch
    ipc_buffer_size: int
    # Reserved for future use
    reserved_3: bytes | None = None

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


def _format_version(version: tuple[int, ...]) -> str:
    """Format a version tuple into a string representation, removing trailing zeros."""
    parts = list(version)
    while len(parts) > 2 and parts[-1] == 0:
        parts.pop()
    return "v" + ".".join(str(part) for part in parts)


def _version_message(version: tuple[int, ...]) -> messages.Version:
    return messages.Version(**dict(zip(("major", "minor", "patch", "build"), version)))


def load(
    session: Session,
    header: bytes,
    chunks: list[bytes],
    chunk_hashes: list[bytes],
    proof: bytes,
    root_packet: bytes,
    min_version: Optional[tuple[int, int, int, int]],
    match_fingerprint: bool = False,
) -> int:
    """Load an external application onto the device.

    Returns:
        Instance ID of the loaded app
    """
    if len(chunks) != len(chunk_hashes):
        raise ValueError(
            f"Number of chunks({len(chunks)}) and chunk_hashes ({len(chunk_hashes)}) are not the same."
        )

    header_parsed = AppHeader.parse(header)

    if min_version is not None:
        min_version_info = f"{_format_version(min_version)}+"
        if header_parsed.version < min_version:
            raise ValueError(
                "Application version "
                f"{_format_version(header_parsed.version)} "
                "is less than the minimum required version "
                f"{_format_version(min_version)}"
            )
    else:
        min_version_info = ""
        min_version = header_parsed.version

    print(f"Requesting {header_parsed.id} {min_version_info}")

    fingerprint = header_parsed.fingerprint() if match_fingerprint else None

    # Send a request to the device to load the app, providing the hash, app ID, and minimum version.
    resp = session.call(
        messages.ExtAppLoad(
            fingerprint=fingerprint,
            id=header_parsed.id,
            version=_version_message(min_version),
        )
    )

    # If the device requests the binary, we proceed to upload it.
    if isinstance(resp, messages.ExtAppHeaderRequest):
        rp = RootPacket.parse(root_packet)
        # Send the header and proof to the device

        resp = session.call(
            messages.ExtAppHeaderAck(
                header=header,
                proof=proof,
                root_packet_timestamp=rp.auth.timestamp,
            )
        )

        if isinstance(resp, messages.ExtAppRootPacketRequest):
            resp = session.call(messages.ExtAppRootPacketAck(root_packet=root_packet))

        print(
            f"Uploading {header_parsed.id} {_format_version(header_parsed.version)} ({sum(len(chunk) for chunk in chunks) / 1024:.1f} KB)"
        )
        # Send the payload in chunks as requested by the device
        while isinstance(resp, messages.ExtAppDataChunkRequest):
            chunk = chunks[resp.index]
            chunk_hash = chunk_hashes[resp.index]
            resp = session.call(
                messages.ExtAppDataChunkAck(data=chunk, hash=chunk_hash)
            )

    # After the upload, the device should respond with ExtAppLoaded containing the instance ID.
    resp = messages.ExtAppLoaded.ensure_isinstance(resp)
    return resp.instance_id


def load_tapp(
    session: Session,
    tapp_file: Path,
    min_version: Optional[tuple[int, int, int, int]] = None,
    match_fingerprint: bool = False,
) -> int:
    """Load a serialized external application (`.tapp`) onto the device.

    The proof is expected next to the app, sharing its name with a `.proof`
    suffix, and the root packets in the `root-packets` directory of the
    serialized artifacts tree (`<root>/<app_id>/<version>/<app>.tapp`).

    Returns:
        Instance ID of the loaded app
    """
    if not tapp_file.is_file():
        raise FileNotFoundError(f"App file not found: {tapp_file}")
    with open(tapp_file, "rb") as f:
        app_json = json.load(f)
    header = base64.b64decode(app_json["header"])

    proof_path = tapp_file.with_suffix(".proof")
    if not proof_path.is_file():
        raise FileNotFoundError(f"App proof not found: {proof_path}")
    with open(proof_path, "rb") as f:
        proof_json = json.load(f)
    proof = bytes.fromhex("".join(proof_json["proof"]))

    # Pick the root packet based on the app ring stored in the app header:
    # ring 0 -> rootpacket_ring0, rings 1 and 2 -> rootpacket_ring12.
    app_ring = AppHeader.parse(header).app_ring
    root_packet_name = (
        "rootpacket_ring0.tmr" if app_ring == 0 else "rootpacket_ring12.tmr"
    )
    root_packet_path = (
        tapp_file.parent.parent.parent / "root-packets" / root_packet_name
    )
    if not root_packet_path.is_file():
        raise FileNotFoundError(f"Root packet not found: {root_packet_path}")
    with open(root_packet_path, "rb") as f:
        root_packet_json = json.load(f)
    root_packet = base64.b64decode(root_packet_json["root_packet"])

    return load(
        session,
        header=header,
        chunks=[base64.b64decode(chunk) for chunk in app_json["chunks"]],
        chunk_hashes=[bytes.fromhex(hash) for hash in app_json["chunk_hashes"]],
        proof=proof,
        root_packet=root_packet,
        min_version=min_version,
        match_fingerprint=match_fingerprint,
    )
