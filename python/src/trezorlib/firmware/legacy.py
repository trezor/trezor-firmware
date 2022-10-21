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
from dataclasses import field

import construct as c
import ecdsa
from construct_classes import Struct, subcon

from . import consts, util
from .core import FirmwareImage

__all__ = [
    "LegacyFirmware",
    "LegacyV2Firmware",
    "check_sig_v1",
]


def check_sig_v1(
    digest: bytes,
    key_indexes: t.Sequence[int],
    signatures: t.Sequence[bytes],
    public_keys: t.Sequence[bytes],
) -> None:
    """Validate signatures of `digest` using the Trezor One V1 method."""
    distinct_indexes = set(i for i in key_indexes if i != 0)
    if not distinct_indexes:
        raise util.Unsigned

    if len(distinct_indexes) < len(key_indexes):
        raise util.InvalidSignatureError(
            f"Not enough distinct signatures (found {len(distinct_indexes)}, need {len(key_indexes)})"
        )

    for i in range(len(key_indexes)):
        key_idx = key_indexes[i] - 1
        signature = signatures[i]

        if key_idx >= len(public_keys):
            # unknown pubkey
            raise util.InvalidSignatureError(f"Unknown key in slot {i}")

        pubkey = public_keys[key_idx][1:]
        verify = ecdsa.VerifyingKey.from_string(pubkey, curve=ecdsa.curves.SECP256k1)
        try:
            verify.verify_digest(signature, digest)
        except ecdsa.BadSignatureError as e:
            raise util.InvalidSignatureError(f"Invalid signature in slot {i}") from e


class LegacyV2Firmware(FirmwareImage):
    """Firmware image in the format used by Trezor One 1.8.0 and newer."""

    HASH_PARAMS = util.FirmwareHashParameters(
        hash_function=hashlib.sha256,
        chunk_size=consts.ONEV2_CHUNK_SIZE,
        padding_byte=b"\xff",
    )

    def verify(
        self, public_keys: t.Sequence[bytes] = consts.V1_BOOTLOADER_KEYS
    ) -> None:
        self.validate_code_hashes()
        check_sig_v1(
            self.digest(),
            self.header.v1_key_indexes,
            self.header.v1_signatures,
            public_keys,
        )

    def verify_unsigned(self) -> None:
        self.validate_code_hashes()
        if any(i != 0 for i in self.header.v1_key_indexes):
            raise util.InvalidSignatureError("Firmware is not unsigned.")


class LegacyFirmware(Struct):
    """Legacy firmware image.
    Consists of a custom header and code block.
    This is the expected format of firmware binaries for Trezor One pre-1.8.0.

    The code block can optionally be interpreted as a new-style firmware image. That is the
    expected format of firmware binary for Trezor One version 1.8.0, which can be installed
    by both the older and the newer bootloader."""

    key_indexes: t.List[int]
    signatures: t.List[bytes]
    code: bytes
    flags: t.Dict[str, t.Any] = field(default_factory=dict)
    embedded_v2: t.Optional[LegacyV2Firmware] = subcon(LegacyV2Firmware, default=None)

    # fmt: off
    SUBCON = c.Struct(
        "magic" / c.Const(b"TRZR"),
        "code_length" / c.Rebuild(c.Int32ul, c.len_(c.this.code)),
        "key_indexes" / c.Int8ul[consts.V1_SIGNATURE_SLOTS],  # pylint: disable=E1136
        "flags" / c.BitStruct(
            c.Padding(7),
            "restore_storage" / c.Flag,
        ),
        "_reserved" / c.Padding(52),
        "signatures" / c.Bytes(64)[consts.V1_SIGNATURE_SLOTS],
        "code" / c.Bytes(c.this.code_length),
        c.Terminated,

        "embedded_v2" / c.RestreamData(c.this.code, c.Optional(LegacyV2Firmware.SUBCON)),
    )
    # fmt: on

    def digest(self) -> bytes:
        return hashlib.sha256(self.code).digest()

    def verify(
        self, public_keys: t.Sequence[bytes] = consts.V1_BOOTLOADER_KEYS
    ) -> None:
        check_sig_v1(
            self.digest(),
            self.key_indexes,
            self.signatures,
            public_keys,
        )

        if self.embedded_v2:
            self.embedded_v2.verify(consts.V1_BOOTLOADER_KEYS)
