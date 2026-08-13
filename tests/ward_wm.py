# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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

"""A mock WARD Manager: the external freshness authority, for tests.

A real WM keeps `(counter, mac)` per wallet and signs it on demand. It is NOT trusted with
contents and could not learn them if it wanted to: `mac` is an HMAC under a device-only
key, so the WM signs a value it cannot compute. Its whole power is to say "this pair is
current", and its whole attack surface is to say that about a pair the wallet really did
reach at some point.

This mock keeps that division honest. It holds ONLY `(counter, mac)` per ward_id and the
signing key -- it never sees a root, an identifier or a value, and it has no way to derive
one. A test that needs a mac must compute it with the device's own key via
`tests/ward_keys.py`, exactly as the device does, which is also what stops this file from
quietly becoming an oracle that a real WM could not be.
"""

from __future__ import annotations

from typing import Optional

from trezorlib import _ed25519

__all__ = ["MockWM", "DEBUG_WM_SEED"]

# The well-known debug WM key. Firmware compiles in its public key and accepts it on
# debug builds only; a release build ships an all-zero placeholder and rejects everything.
DEBUG_WM_SEED = b"AUTHDB QM DEBUG KEY SEED v1 ...."

_ATTEST_DOMAIN = b"WARD ATTEST v1"
_ATTEST_VERSION = 1


class MockWM:
    """The freshness authority. Knows counters and macs; knows nothing about contents."""

    def __init__(self, seed: bytes = DEBUG_WM_SEED) -> None:
        self._seed = seed
        self._pub = _ed25519.publickey_unsafe(seed)
        # ward_id -> (counter, mac). Deliberately not a root: a real WM never sees one.
        self._heads: dict[bytes, tuple[int, bytes]] = {}

    @property
    def pubkey(self) -> bytes:
        return self._pub

    def publish(self, ward_id: bytes, counter: int, mac: bytes) -> None:
        """Record what the wallet says is current.

        A real WM would take this from a device-authenticated write. It cannot check the
        mac -- that is the point -- so it records what it is told and its signature means
        only "this is what I was told, and it is the latest I hold".
        """
        self._heads[ward_id] = (counter, mac)

    def head(self, ward_id: bytes) -> Optional[tuple[int, bytes]]:
        return self._heads.get(ward_id)

    def attest(self, ward_id: bytes, nonce: bytes) -> tuple[int, bytes, bytes]:
        """Sign the current (counter, mac) against this round's nonce.

        Returns (counter, mac, signature). The nonce binding is what makes the answer
        fresh rather than merely authentic.
        """
        counter, mac = self._heads[ward_id]
        return counter, mac, self.sign(ward_id, nonce, counter, mac)

    def sign(self, ward_id: bytes, nonce: bytes, counter: int, mac: bytes) -> bytes:
        """Sign an arbitrary (counter, mac) -- used by tests that model a hostile WM."""
        message = (
            _ATTEST_DOMAIN
            + bytes([_ATTEST_VERSION])
            + nonce
            + ward_id
            + counter.to_bytes(4, "big")
            + mac
        )
        return _ed25519.signature_unsafe(message, self._seed, self._pub)
