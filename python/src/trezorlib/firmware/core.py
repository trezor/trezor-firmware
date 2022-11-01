# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
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

import hashlib
import typing as t
from copy import copy
from enum import Enum

import construct as c
from construct_classes import Struct, subcon

from .. import cosi
from ..tools import EnumAdapter, TupleAdapter
from . import consts, util
from .vendor import VendorHeader

__all__ = [
    "HeaderType",
    "FirmwareHeader",
    "FirmwareImage",
    "VendorFirmware",
]


class HeaderType(Enum):
    FIRMWARE = b"TRZF"
    BOOTLOADER = b"TRZB"


class FirmwareHeader(Struct):
    magic: HeaderType
    header_len: int
    expiry: int
    code_length: int
    version: t.Tuple[int, int, int, int]
    fix_version: t.Tuple[int, int, int, int]
    hashes: t.Sequence[bytes]

    v1_signatures: t.Sequence[bytes]
    v1_key_indexes: t.Sequence[int]

    sigmask: int
    signature: bytes

    # fmt: off
    SUBCON = c.Struct(
        "_start_offset" / c.Tell,
        "magic" / EnumAdapter(c.Bytes(4), HeaderType),
        "header_len" / c.Int32ul,
        "expiry" / c.Int32ul,
        "code_length" / c.Rebuild(
            c.Int32ul,
            lambda this:
                len(this._.code) if "code" in this._
                else (this.code_length or 0)
        ),
        "version" / TupleAdapter(c.Int8ul, c.Int8ul, c.Int8ul, c.Int8ul),
        "fix_version" / TupleAdapter(c.Int8ul, c.Int8ul, c.Int8ul, c.Int8ul),
        "_reserved" / c.Padding(8),
        "hashes" / c.Bytes(32)[16],

        "v1_signatures" / c.Bytes(64)[consts.V1_SIGNATURE_SLOTS],
        "v1_key_indexes" / c.Int8ul[consts.V1_SIGNATURE_SLOTS],  # pylint: disable=E1136

        "_reserved" / c.Padding(220),
        "sigmask" / c.Byte,
        "signature" / c.Bytes(64),

        "_end_offset" / c.Tell,

        "_rebuild_header_len" / c.If(
            c.this.version[0] > 1,
            c.Pointer(
                c.this._start_offset + 4,
                c.Rebuild(c.Int32ul, c.this._end_offset - c.this._start_offset)
            ),
        ),
    )
    # fmt: on


class FirmwareImage(Struct):
    """Raw firmware image.

    Consists of firmware header and code block.
    This is the expected format of firmware binaries for Trezor One, or bootloader images
    for Trezor T."""

    header: FirmwareHeader = subcon(FirmwareHeader)
    _code_offset: int
    code: bytes

    SUBCON = c.Struct(
        "header" / FirmwareHeader.SUBCON,
        "_code_offset" / c.Tell,
        "code" / c.Bytes(c.this.header.code_length),
        c.Terminated,
    )

    HASH_PARAMS = util.FirmwareHashParameters(
        hash_function=hashlib.blake2s,
        chunk_size=consts.V2_CHUNK_SIZE,
        padding_byte=None,
    )

    def code_hashes(self) -> t.List[bytes]:
        """Calculate hashes of chunks of `code`.

        Assume that the first `code_offset` bytes of `code` are taken up by the header.
        """
        hashes = []
        # End offset for each chunk. Normally this would be (i+1)*chunk_size for i-th chunk,
        # but the first chunk is shorter by code_offset, so all end offsets are shifted.
        ends = [
            (i + 1) * self.HASH_PARAMS.chunk_size - self._code_offset for i in range(16)
        ]
        start = 0
        for end in ends:
            chunk = self.code[start:end]
            # padding for last non-empty chunk
            if (
                self.HASH_PARAMS.padding_byte is not None
                and start < len(self.code)
                and end > len(self.code)
            ):
                chunk += self.HASH_PARAMS.padding_byte[0:1] * (end - start - len(chunk))

            if not chunk:
                hashes.append(b"\0" * 32)
            else:
                hashes.append(self.HASH_PARAMS.hash_function(chunk).digest())

            start = end

        return hashes

    def validate_code_hashes(self) -> None:
        if self.code_hashes() != self.header.hashes:
            raise util.FirmwareIntegrityError("Invalid firmware data.")

    def digest(self) -> bytes:
        header = copy(self.header)
        header.hashes = self.code_hashes()
        header.signature = b"\x00" * 64
        header.sigmask = 0
        header.v1_key_indexes = [0] * consts.V1_SIGNATURE_SLOTS
        header.v1_signatures = [b"\x00" * 64] * consts.V1_SIGNATURE_SLOTS
        return self.HASH_PARAMS.hash_function(header.build()).digest()


class VendorFirmware(Struct):
    """Firmware image prefixed by a vendor header.

    This is the expected format of firmware binaries for Trezor T."""

    vendor_header: VendorHeader = subcon(VendorHeader)
    firmware: FirmwareImage = subcon(FirmwareImage)

    SUBCON = c.Struct(
        "vendor_header" / VendorHeader.SUBCON,
        "firmware" / FirmwareImage.SUBCON,
        c.Terminated,
    )

    def digest(self) -> bytes:
        return self.firmware.digest()

    def verify(self, _public_keys: t.Sequence[bytes] = ()) -> None:
        if _public_keys:
            raise ValueError("Cannot supply custom keys for vendor firmware.")

        self.firmware.validate_code_hashes()

        self.vendor_header.verify()
        digest = self.digest()
        try:
            cosi.verify(
                self.firmware.header.signature,
                digest,
                self.vendor_header.sig_m,
                self.vendor_header.pubkeys,
                self.firmware.header.sigmask,
            )
        except Exception:
            raise util.InvalidSignatureError("Invalid firmware signature.")

        # XXX expiry is not used now
        # now = time.gmtime()
        # if time.gmtime(fw.vendor_header.expiry) < now:
        #     raise ValueError("Vendor header expired.")
