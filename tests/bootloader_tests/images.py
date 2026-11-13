# This file is part of the Trezor project.
#
# Copyright (C) 2012-2026 SatoshiLabs and contributors
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

"""Firmware images for bootloader tests.

A bootloader built with the development keys accepts an image signed with
them. The images built here carry no code that runs: the emulator never
executes firmware, it only verifies it. That is enough for the install,
upgrade and boot flows, and lets a test choose the version, vendor and
model of each image.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from trezorlib import cosi
from trezorlib._internal import firmware_headers
from trezorlib.firmware.core import FirmwareHeader, HeaderType
from trezorlib.firmware.models import Model
from trezorlib.firmware.secmon import SecmonHeader

ROOT = Path(__file__).resolve().parent.parent.parent
VENDOR_HEADERS = ROOT / "core" / "embed" / "models"

# IMAGE_HEADER_SIZE and SECMON_HEADER_SIZE in core/embed/sec/image/inc/sec/image.h
IMAGE_HEADER_SIZE = 1024
SECMON_HEADER_SIZE = 0x200

# Checked-in vendor headers signed with the development bootloader keys.
VENDORS = {
    # full trust: no warning, no click, installs without a confirmation
    "dev": "vendorheader_dev_DO_NOT_SIGN_signed_dev.bin",
    # untrusted: red warning screen with a click, confirmation before install
    "unsafe": "vendorheader_unsafe_signed_dev.bin",
}


def vendor_header(model: str, vendor: str = "dev") -> bytes:
    return (VENDOR_HEADERS / model / "vendorheader" / VENDORS[vendor]).read_bytes()


def _filler(size: int, seed: bytes) -> bytes:
    """Deterministic bytes that look like code."""
    data = b""
    counter = 0
    while len(data) < size:
        data += hashlib.sha256(seed + counter.to_bytes(4, "little")).digest()
        counter += 1
    return data[:size]


def _align(value: int, alignment: int) -> int:
    return (value + alignment - 1) & ~(alignment - 1)


def make_secmon(
    model: str,
    *,
    version: tuple[int, int, int, int] = (1, 0, 0, 0),
    monotonic: int = 0,
    code_size: int = 4096 - SECMON_HEADER_SIZE,
    seed: bytes = b"bootloader-tests-secmon",
) -> bytes:
    """Build a dev-key signed secure-monitor image (`TSEC`) for `model`."""
    if (SECMON_HEADER_SIZE + code_size) % 512 or SECMON_HEADER_SIZE + code_size < 4096:
        raise ValueError("code_size must make the image a multiple of 512 B, >= 4 KiB")

    code = _filler(code_size, seed)
    header = SecmonHeader.SUBCON.build(
        dict(
            header_len=SECMON_HEADER_SIZE,
            code_length=code_size,
            version=version,
            hw_model=Model[model],
            hw_revision=0,
            monotonic=monotonic,
            reserved_0=b"\0" * 2,
            hash=b"\0" * 32,
            reserved_1=b"\0" * 391,
            sigmask=0,
            signature=b"\0" * 64,
        )
    )
    assert len(header) == SECMON_HEADER_SIZE

    image = firmware_headers.SecmonImage.parse(header + code)
    image.header.hash = image.code_hash()
    privkeys = image.DEV_KEYS
    signature = cosi.sign_with_privkeys(image.digest(), privkeys, deterministic=True)
    image.insert_signature(signature, (1 << len(privkeys)) - 1)
    data = image.build()
    firmware_headers.SecmonImage.parse(data).verify(dev_keys=True)
    return data


def make_firmware(
    model: str,
    *,
    vendor: str = "dev",
    version: tuple[int, int, int, int] = (2, 9, 0, 0),
    fix_version: tuple[int, int, int, int] = (2, 0, 0, 0),
    monotonic: int = 0,
    code_size: int = 15 * 1024,
    seed: bytes = b"bootloader-tests",
    secmon: bool = False,
    code_alignment: int = 0x200,
) -> bytes:
    """Build a dev-key signed firmware image for `model`.

    `code_size` plus the header must be at least 4 KiB and a multiple of
    512 bytes, as the bootloader requires. The code is deterministic for
    a given `seed`, so two images with the same parameters are identical.

    On models that verify a secure monitor (`secmon=True`) the code starts,
    at the model's `code_alignment` past the headers, with a signed secmon
    image, which is what the bootloader looks for there.
    """
    if (IMAGE_HEADER_SIZE + code_size) % 512 or IMAGE_HEADER_SIZE + code_size < 4096:
        raise ValueError("code_size must make the image a multiple of 512 B, >= 4 KiB")

    vendor_data = vendor_header(model, vendor)
    code = _filler(code_size, seed)
    if secmon:
        headers_len = len(vendor_data) + IMAGE_HEADER_SIZE
        offset = _align(headers_len, code_alignment) - headers_len
        secmon_data = make_secmon(model, monotonic=monotonic)
        if offset + len(secmon_data) > code_size:
            raise ValueError("code_size too small for the secmon image")
        code = code[:offset] + secmon_data + code[offset + len(secmon_data) :]

    header = FirmwareHeader.SUBCON.build(
        dict(
            magic=HeaderType.FIRMWARE,
            header_len=IMAGE_HEADER_SIZE,
            # bit 0 set: an image for the current generation of bootloaders
            expiry=1,
            code_length=code_size,
            version=version,
            fix_version=fix_version,
            hw_model=Model[model],
            hw_revision=0,
            monotonic=monotonic,
            reserved_0=b"\0" * 2,
            hashes=[b"\0" * 32] * 16,
            v1_signatures=[b"\0" * 64] * 3,
            v1_key_indexes=[0] * 3,
            reserved_1=b"\0" * 220,
            sigmask=0,
            signature=b"\0" * 64,
        )
    )
    assert len(header) == IMAGE_HEADER_SIZE

    image = firmware_headers.VendorFirmware.parse(vendor_data + header + code)
    image.firmware.header.hashes = image.firmware.code_hashes()
    privkeys = image.DEV_KEYS
    signature = cosi.sign_with_privkeys(image.digest(), privkeys, deterministic=True)
    image.insert_signature(signature, (1 << len(privkeys)) - 1)
    data = image.build()

    # the bootloader built with the development keys must accept it
    firmware_headers.VendorFirmware.parse(data).verify(dev_keys=True)
    return data
