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
_ATTEST_VERSION = 2


class MockWM:
    """The freshness authority. Knows counters and macs; knows nothing about contents."""

    def __init__(self, seed: bytes = DEBUG_WM_SEED) -> None:
        self._seed = seed
        self._pub = _ed25519.publickey_unsafe(seed)
        # ward_id -> (counter, mac, timestamp). Deliberately not a root: a real WM never
        # sees one, and could not compute a mac if it did.
        self._heads: dict[bytes, tuple[int, bytes, int]] = {}

    @property
    def pubkey(self) -> bytes:
        return self._pub

    def publish(self, ward_id: bytes, counter: int, mac: bytes, timestamp: int) -> None:
        # timestamp is REQUIRED, not defaulted. A default lets a caller publish at one time
        # and ingest at another; the signature then covers a different timestamp than the
        # message carries, and the test fails as "verification failed" -- which reads like a
        # firmware bug rather than a test bug. Make the omission impossible instead.
        """Record what the wallet says is current.

        A real WM would take this from a device-authenticated write. It cannot check the
        mac -- that is the point -- so it records what it is told and its signature means
        only "this is what I was told, and it is the latest I hold".
        """
        self._heads[ward_id] = (counter, mac, timestamp)

    def head(self, ward_id: bytes) -> Optional[tuple[int, bytes, int]]:
        return self._heads.get(ward_id)

    def attest(self, ward_id: bytes, nonce: bytes) -> tuple[int, bytes, int, bytes]:
        """Sign the current (counter, mac, timestamp) against this round's nonce.

        Returns (counter, mac, timestamp, signature). The nonce binding is what makes the
        answer fresh rather than merely authentic.
        """
        counter, mac, timestamp = self._heads[ward_id]
        return (
            counter,
            mac,
            timestamp,
            self.sign(ward_id, nonce, counter, mac, timestamp),
        )

    # --- publish-and-attest, as one operation -----------------------------------------------

    class Conflict(Exception):
        """The head this transition was built on is not the head the WM holds."""

        def __init__(self, head_counter: int) -> None:
            super().__init__(f"WM head is at {head_counter}")
            self.head_counter = head_counter

    def publish_and_attest(
        self,
        ward_id: bytes,
        nonce: bytes,
        from_counter: int,
        from_mac: bytes,
        to_counter: int,
        to_mac: bytes,
        wm_sig: bytes,
        timestamp: int,
        head_init_sig: Optional[bytes] = None,
    ) -> tuple[int, bytes, int, bytes]:
        """Install a head and attest it, atomically. Returns (counter, mac, timestamp, sig).

        ONE OPERATION, NOT TWO, and that is the point of replacing `publish` + `attest`. Between a
        separate CAS and a separate attest another device can win: D1 advances 41->42, D2 advances
        42->43, and D1's attest then describes 43 -- a head D1 did not publish. The device would
        reject it, having minted neither that counter nor that mac, but its own write would already
        have landed with no way to learn so. Attesting the head THIS call created removes the
        window rather than detecting it afterwards.

        THE SIGNATURE IS OVER MAC HEADS, so a WM verifies exactly what it stores. It is checked
        against `ward_id`, which IS the verifying key -- so there is no enrolment and no second
        per-wallet value.

        A wallet the WM has never seen has no head to compare against, so the first call must carry
        `head_init_sig` authorising the starting pair. Anyone could otherwise claim a wallet's
        opening head by being first to speak.
        """
        from .ward_keys import verify_head_init_sig, verify_wm_sig

        known = self._heads.get(ward_id)

        if known is None:
            if head_init_sig is None:
                raise ValueError("unknown ward_id and no head-init authorisation")
            if not verify_head_init_sig(ward_id, from_mac, head_init_sig):
                raise ValueError("head-init authorisation does not verify")
            if from_counter != 0:
                raise ValueError("a wallet's first head must start at counter 0")
            self._heads[ward_id] = (from_counter, from_mac, timestamp)
            known = self._heads[ward_id]

        # COMPARE-AND-SWAP. Refusing an advance from a head we do not hold is what stops two
        # devices both believing they wrote counter N.
        head_counter, head_mac, _ts = known
        if (head_counter, head_mac) != (from_counter, from_mac):
            raise MockWM.Conflict(head_counter)

        if to_counter != from_counter + 1:
            raise ValueError("a head advances by exactly one")

        if not verify_wm_sig(
            ward_id, from_counter, from_mac, to_counter, to_mac, wm_sig
        ):
            raise ValueError("transition is not authorised by this wallet")

        self._heads[ward_id] = (to_counter, to_mac, timestamp)
        return (
            to_counter,
            to_mac,
            timestamp,
            self.sign(ward_id, nonce, to_counter, to_mac, timestamp),
        )

    def attest_head(
        self, ward_id: bytes, nonce: bytes, current_mac: bytes, head_init_sig: bytes
    ) -> tuple[int, bytes, int, bytes]:
        """Attest the current head, adopting the wallet's opening head if it is unknown.

        What a read-only first use needs: a device asks for the current head before it has ever
        written, so there may be nothing to attest yet. Same authorisation as above -- the WM
        cannot compute a mac, so an opening head has to be supplied and signed.
        """
        from .ward_keys import verify_head_init_sig

        if ward_id not in self._heads:
            if not verify_head_init_sig(ward_id, current_mac, head_init_sig):
                raise ValueError("head-init authorisation does not verify")
            self._heads[ward_id] = (0, current_mac, 0)

        return self.attest(ward_id, nonce)

    def sign(
        self, ward_id: bytes, nonce: bytes, counter: int, mac: bytes, timestamp: int
    ) -> bytes:
        """Sign arbitrary values -- used by tests that model a hostile or broken WM."""
        message = (
            _ATTEST_DOMAIN
            + bytes([_ATTEST_VERSION])
            + nonce
            + ward_id
            + counter.to_bytes(4, "big")
            + mac
            + timestamp.to_bytes(8, "big")
        )
        return _ed25519.signature_unsafe(message, self._seed, self._pub)
