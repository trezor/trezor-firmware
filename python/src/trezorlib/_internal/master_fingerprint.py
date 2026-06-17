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

import hashlib
from typing import TextIO

from .slip26 import parse_label

# Artefact info and fingerprint: (model integer, purpose, 32-byte fingerprint).
ArtefactFingerprint = tuple[int, int, bytes]


def parse_fingerprints_file(f: TextIO) -> set[ArtefactFingerprint]:
    """Parse ``<label>: HEX`` lines (as produced by firmware-fingerprint.py) into
    ``(model, purpose, fingerprint)`` targets.

    Blank lines and comments starting with ``#`` are ignored.
    """
    result: set[ArtefactFingerprint] = set()
    for lineno, raw in enumerate(f.read().splitlines(), 1):
        line = raw.split("#", 1)[0].strip()  # drop comments
        if not line:
            continue

        label, sep, hex_fingerprint = line.partition(":")
        if not sep:
            raise ValueError(f"{f.name}:{lineno}: expected 'label: HEX', got {raw!r}")

        try:
            model, purpose = parse_label(label.strip())
        except ValueError as e:
            raise ValueError(f"{f.name}:{lineno}: {e}") from e

        try:
            # whitespace between hex digits is allowed, e.g. "1111 2222 ..."
            fingerprint = bytes.fromhex("".join(hex_fingerprint.split()))
        except ValueError:
            raise ValueError(f"{f.name}:{lineno}: invalid hex") from None

        if len(fingerprint) != 32:
            raise ValueError(
                f"{f.name}:{lineno}: fingerprint must be 32 bytes, got {len(fingerprint)}"
            )

        result.add((model, purpose, fingerprint))

    return result


def master_fingerprint(fingerprints: set[ArtefactFingerprint]) -> bytes:
    """Hash the targets into the master fingerprint, in canonical order."""
    if not fingerprints:
        raise ValueError("no fingerprints found")

    ctx = hashlib.sha256()
    for model, purpose, fingerprint in sorted(fingerprints):
        ctx.update(model.to_bytes(4, "little"))
        ctx.update(purpose.to_bytes(1, "little"))
        ctx.update(fingerprint)
    return ctx.digest()
