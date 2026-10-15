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

import construct as c
import pytest

from trezorlib.extapp import AppHeader, AppImage

HEADER_SIZE = 512
CHUNK_SIZE = 4
PAYLOAD = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09"


def chunk_hash(payload: bytes) -> bytes:
    hash = b"\x00" * 32
    chunks = [payload[i : i + CHUNK_SIZE] for i in range(0, len(payload), CHUNK_SIZE)]
    for chunk in reversed(chunks):
        hash = sha256(hash + chunk).digest()
    return hash


def header_bytes(code_size: int) -> bytes:
    return AppHeader.SUBCON.build(
        dict(
            header_size=HEADER_SIZE,
            id="test.example.com",
            name="Test",
            vendor="Example",
            model="T3W1",
            version=(1, 2, 3, 4),
            sdk_version=(0, 1, 0, 0),
            abi_version=1,
            target_arch=0,
            app_ring=2,
            language=0,
            code_size=code_size,
            data_size=1024,
            chunk_hash=chunk_hash(PAYLOAD),
            chunk_size=CHUNK_SIZE,
            curves=["secp256k1"],
            paths=["m/44'/1'"],
            ipc_buffer_size=4096,
        )
    )


def test_parse_valid() -> None:
    image = AppImage.parse(header_bytes(len(PAYLOAD)) + PAYLOAD, strict=True)
    assert image.payload == PAYLOAD
    assert image.header.code_size == len(PAYLOAD)
    assert [chunk for chunk, _ in image.chunks()] == [
        PAYLOAD[0:4],
        PAYLOAD[4:8],
        PAYLOAD[8:],
    ]
    assert image.build() == header_bytes(len(PAYLOAD)) + PAYLOAD


def test_parse_truncated_payload() -> None:
    data = header_bytes(len(PAYLOAD)) + PAYLOAD[:-1]
    with pytest.raises(c.StreamError):
        AppImage.parse(data)


def test_parse_trailing_bytes() -> None:
    # `code_size` covers only part of the payload, the hash covers all of it
    data = header_bytes(4) + PAYLOAD
    with pytest.raises(c.TerminatedError):
        AppImage.parse(data)


def test_build_payload_size_mismatch() -> None:
    header = AppHeader.parse(header_bytes(len(PAYLOAD)))
    image = AppImage(header=header, payload=PAYLOAD[:-1])
    with pytest.raises(c.StreamError):
        image.build()
