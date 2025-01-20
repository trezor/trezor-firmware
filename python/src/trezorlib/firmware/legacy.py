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

from __future__ import annotations

import hashlib
import typing as t
from dataclasses import field

import construct as c
import ecdsa
from construct_classes import Struct, subcon

from . import consts, models, util
from .core import FirmwareImage
from .models import Model

__all__ = [
    "LegacyFirmware",
    "LegacyV2Firmware",
    "check_sig_v1",
]


ZERO_SIG = b"\x00" * 64


def check_sig_v1(
    digest: bytes,
    key_indexes: t.Sequence[int],
    signatures: t.Sequence[bytes],
    sigs_required: int,
    public_keys: t.Sequence[bytes],
) -> None:
    """Validate signatures of `digest` using the Trezor One V1 method."""
    distinct_indexes = set(i for i in key_indexes[:sigs_required] if i != 0)
    if not distinct_indexes:
        raise util.Unsigned

    if len(distinct_indexes) != sigs_required:
        raise util.InvalidSignatureError(
            f"Not enough distinct signatures (found {len(distinct_indexes)}, need {sigs_required})"
        )

    if any(k != 0 for k in key_indexes[sigs_required:]) or any(
        sig != ZERO_SIG for sig in signatures[sigs_required:]
    ):
        raise util.InvalidSignatureError("Too many signatures")

    for i in range(sigs_required):
        key_idx = key_indexes[i] - 1
        signature = signatures[i]

        if key_idx >= len(public_keys):
            # unknown pubkey
            raise util.InvalidSignatureError(f"Unknown key in slot {i}")

        verify = ecdsa.VerifyingKey.from_string(
            public_keys[key_idx],
            curve=ecdsa.curves.SECP256k1,
            hashfunc=hashlib.sha256,
        )
        try:
            verify.verify_digest(signature, digest)
        except ecdsa.BadSignatureError as e:
            raise util.InvalidSignatureError(f"Invalid signature in slot {i}") from e


def check_sig_signmessage(
    digest: bytes,
    key_indexes: t.Sequence[int],
    signatures: t.Sequence[bytes],
    sigs_required: int,
    public_keys: t.Sequence[bytes],
) -> None:
    """Validate signatures of `digest` using the Trezor One SignMessage method."""
    btc_digest = hashlib.sha256(b"\x18Bitcoin Signed Message:\n\x20" + digest).digest()
    final_digest = hashlib.sha256(btc_digest).digest()
    check_sig_v1(
        final_digest,
        key_indexes,
        signatures,
        sigs_required,
        public_keys,
    )


class LegacyV2Firmware(FirmwareImage):
    """Firmware image in the format used by Trezor One 1.8.0 and newer."""

    V3_FIRST_VERSION = (1, 12, 0)

    def get_hash_params(self) -> util.FirmwareHashParameters:
        return Model.ONE.hash_params()

    def verify_v2(self, dev_keys: bool) -> None:
        if not dev_keys:
            public_keys = models.LEGACY_V1V2.firmware_keys
        else:
            public_keys = models.LEGACY_V1V2_DEV.firmware_keys

        self.validate_code_hashes()
        check_sig_v1(
            self.digest(),
            self.header.v1_key_indexes,
            self.header.v1_signatures,
            models.LEGACY_V1V2.firmware_sigs_needed,
            public_keys,
        )

    def verify_v3(self, dev_keys: bool) -> None:
        if not dev_keys:
            model_keys = models.LEGACY_V3
        else:
            model_keys = models.LEGACY_V3_DEV

        self.validate_code_hashes()
        check_sig_signmessage(
            self.digest(),
            self.header.v1_key_indexes,
            self.header.v1_signatures,
            model_keys.firmware_sigs_needed,
            model_keys.firmware_keys,
        )

    def verify(self, dev_keys: bool = False) -> None:
        if self.header.version >= self.V3_FIRST_VERSION:
            try:
                self.verify_v3(dev_keys)
            except util.InvalidSignatureError:
                pass
            else:
                return

        self.verify_v2(dev_keys)

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

    key_indexes: list[int]
    signatures: list[bytes]
    code: bytes
    flags: dict[str, t.Any] = field(default_factory=dict)
    embedded_v2: LegacyV2Firmware | None = subcon(LegacyV2Firmware, default=None)

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

    def verify(self, dev_keys: bool = False) -> None:
        if not dev_keys:
            model_keys = models.LEGACY_V1V2
        else:
            model_keys = models.LEGACY_V1V2_DEV
        check_sig_v1(
            self.digest(),
            self.key_indexes,
            self.signatures,
            model_keys.firmware_sigs_needed,
            model_keys.firmware_keys,
        )

        if self.embedded_v2:
            self.embedded_v2.verify()

    def model(self) -> Model | None:
        return Model.T1B1
