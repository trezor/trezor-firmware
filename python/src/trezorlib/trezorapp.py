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

import struct
from hashlib import sha256
from typing import TYPE_CHECKING

import construct as c

from . import messages
from .construct_helpers import TupleAdapter

if TYPE_CHECKING:
    from .transport.session import Session


class AppHeader(struct.Struct):
    # Magic number to identify the app binary format
    magic: int
    # Header size in bytes (contains AppHeader::APP_HEADER_SIZE)
    header_size: int
    # Unique identifier of the app
    id: str
    # App version in the format major.minor.patch.build, each as a byte
    version: tuple[int, int, int, int]
    # SDK version that the app was built against
    sdk_version: tuple[int, int]
    # ABI version that the app was built against
    abi_version: int
    # Type of binary payload (e.g., ARMV8M, X86_64)
    payload_type: int
    # Size of binary payload in bytes
    payload_size: int

    # fmt: off
    SUBCON = c.Struct(
        "_start_offset" / c.Tell,
        "magic" / c.Const(b"TRZA"),
        "header_size" / c.Int32ul,
        "id" / c.PaddedString(32, "utf-8"),
        "version" / TupleAdapter(c.Int8ul, c.Int8ul, c.Int8ul, c.Int8ul),
        "sdk_version" / TupleAdapter(c.Int8ul, c.Int8ul),

        "abi_version" / c.Int8ul,
        "payload_type" / c.Int8ul,
        "payload_size" / c.Int32ul,
    )
    # fmt: on


def load(
    session: "Session",
    app_binary: bytes,
    proof: bytes,
    min_version: tuple[int, int] | None,
    force_reload: bool = False,
) -> int:
    """Load an external application onto the device.

    Returns:
        Instance ID of the loaded app
    """

    # Parse the app header to extract metadata
    app_header = AppHeader.SUBCON.parse(app_binary)

    if min_version is None:
        min_version = app_header.version[:2]
    else:
        app_version = app_header.version[:2]
        if app_version < min_version:
            raise ValueError(
                f"App version {app_version} is less than the minimum required version {min_version}"
            )

    hash = None
    if force_reload:
        hash = sha256(app_binary).digest()

    print(
        f"Loading app {app_header.id} version {app_header.version} (min required: {min_version})"
    )

    resp = session.call(
        messages.TrezorAppLoad(
            hash=hash, id=app_header.id, version=min_version, size=len(app_binary)
        )
    )

    # if resp isinstance AppBinaryRequest
    # call AppBinaryAck (header, proof, DEV ONLY root_for_proof)

    while isinstance(resp, messages.DataChunkRequest):
        chunk = app_binary[resp.data_offset : resp.data_offset + resp.data_length]
        resp = session.call(messages.DataChunkAck(data_chunk=chunk))

    resp = messages.TrezorAppLoaded.ensure_isinstance(resp)
    return resp.instance_id
