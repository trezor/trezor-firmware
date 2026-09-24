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

A real WM keeps the authoritative head per wallet and signs, on demand, the STEP that reached it:
`(from_counter, from_root) -> (to_counter, to_root)`. Its whole power is to say "this step is
current", and it is the authority on FRESHNESS and ORDERING and on nothing else.

IT REMEMBERS THE HEAD IT DISPLACED, which is the only structural thing the transition form asks
of it. It already compare-and-swaps on the `from` end, so the value was always in hand -- this
just keeps it.

IT SEES ROOTS, AND THAT IS A DELIBERATE NARROWING OF WHAT IT USED TO BE. The head was once a
`root_mac` under a device-only K_mac, so the WM signed a value it could not compute and was
therefore bounded to replaying states the wallet genuinely reached. That key is gone. This mock
holds `(counter, root)` and can trivially invent one -- and a test that wants to model a hostile
WM should. What refuses an invented root is the DEVICE, which folds an `auth_commit` into every
adoption; minting one needs K_auth, which this file has no access to and must never acquire.

It still sees no identifier and no value: it is told roots, never leaves.
"""

from __future__ import annotations

from typing import Optional

from trezorlib import _ed25519

__all__ = ["MockWM", "DEBUG_WM_SEED"]

# The well-known debug WM key. Firmware compiles in its public key and accepts it on
# debug builds only; a release build ships an all-zero placeholder and rejects everything.
DEBUG_WM_SEED = b"AUTHDB QM DEBUG KEY SEED v1 ...."

_ATTEST_DOMAIN = b"WARD ATTEST v1"
# 3: the 32-byte field became the ROOT rather than a mac over it. 4: the preimage names a
# TRANSITION rather than a single head, so both ends travel.
_ATTEST_VERSION = 4

# The empty tree's stand-in inside a preimage, mirroring apps.ward.attest.EMPTY_ROOT. A head can
# legitimately BE the empty tree -- counter 0, and any wallet drained back to nothing -- so every
# entry point here normalises rather than assuming a root is present.
import hashlib as _hashlib

EMPTY_ROOT = _hashlib.sha256(b"\x03").digest()


def _or_empty(root):
    return root if root is not None else EMPTY_ROOT


class MockWM:
    """The freshness authority. Knows counters and roots; knows nothing about leaves."""

    def __init__(self, seed: bytes = DEBUG_WM_SEED) -> None:
        self._seed = seed
        self._pub = _ed25519.publickey_unsafe(seed)
        # How many demotions this WM has been asked to accept. A real one would apply policy
        # here; recording it is how a test shows the REVERT tag actually reached the WM.
        self.reverts_seen = 0
        # ward_id -> (from_counter, from_root, to_counter, to_root, timestamp). An absent root
        # is the empty tree and is held as EMPTY_ROOT, the form it takes inside the preimage.
        self._heads: dict[bytes, tuple[int, bytes, int, bytes, int]] = {}

    @property
    def pubkey(self) -> bytes:
        return self._pub

    def install_unauthenticated(
        self,
        ward_id: bytes,
        counter: int,
        root: bytes,
        timestamp: int,
        from_counter: "int | None" = None,
        from_root: "bytes | None" = None,
    ) -> None:
        # timestamp is REQUIRED, not defaulted. A default lets a caller publish at one time
        # and ingest at another; the signature then covers a different timestamp than the
        # message carries, and the test fails as "verification failed" -- which reads like a
        # firmware bug rather than a test bug. Make the omission impossible instead.
        """Force a head in with NO authorisation. Not what a real WM does, and named to say so.

        A real WM takes its head from `advance`, which compare-and-swaps and verifies `wm_sig`.
        This exists only to model a WM that has been told something by a party holding no
        signature -- a broken operator, a fixture standing in for history that predates the test,
        a hostile WM inventing state. An ordinary test should never reach for it: it is the thing
        the authorisation exists to prevent, and using it by habit would leave `wm_sig` untested
        while every test still passed.

        The `from` end DEFAULTS to the head being displaced, which is what an ordinary advance
        means; pass it explicitly to model a WM whose predecessor is something else. At counter 0
        it defaults to the head itself -- genesis attests itself, having no predecessor.
        """
        if from_counter is None:
            known = self._heads.get(ward_id)
            if known is not None and counter > 0:
                from_counter, from_root = known[2], known[3]
            else:
                from_counter, from_root = counter, root
        self._heads[ward_id] = (
            from_counter,
            _or_empty(from_root),
            counter,
            _or_empty(root),
            timestamp,
        )

    def head(self, ward_id: bytes) -> Optional[tuple[int, bytes, int]]:
        """The HEAD -- `(counter, root, timestamp)` -- not the step that reached it.

        Named for what callers want: a compare-and-swap needs the current end, and so does a test
        asserting where the WM stands. `attest` is where the predecessor surfaces, because that is
        where it is signed.
        """
        known = self._heads.get(ward_id)
        if known is None:
            return None
        _fc, _fr, counter, root, timestamp = known
        return counter, root, timestamp

    def step(self, ward_id: bytes) -> Optional[tuple]:
        """The whole transition the WM holds: (from_counter, from_root, to_counter, to_root, ts)."""
        return self._heads.get(ward_id)

    def attest(self, ward_id: bytes, nonce: bytes) -> tuple:
        """Sign the current transition against this round's nonce.

        Returns (from_counter, from_root, to_counter, to_root, timestamp, signature). The nonce
        binding is what makes the answer fresh rather than merely authentic.
        """
        fc, fr, counter, root, timestamp = self._heads[ward_id]
        return (
            fc,
            fr,
            counter,
            root,
            timestamp,
            self.sign(ward_id, nonce, fc, fr, counter, root, timestamp),
        )

    # --- publish-and-attest, as one operation -----------------------------------------------

    class Conflict(Exception):
        """The head this transition was built on is not the head the WM holds."""

        def __init__(self, head_counter: int) -> None:
            super().__init__(f"WM head is at {head_counter}")
            self.head_counter = head_counter

    def advance(
        self,
        ward_id: bytes,
        from_counter: int,
        from_root: bytes,
        to_counter: int,
        to_root: bytes,
        wm_sig: bytes,
        timestamp: int,
        head_init_sig: Optional[bytes] = None,
    ) -> bool:
        """Compare-and-swap the head, verifying the wallet's authorisation. Returns is_revert.

        THE AUTHENTICATED WAY IN, and the only one a real host has. Connect mode reaches it on its
        own -- a write is published in one exchange and attested in a later round -- which is why
        this is separate from `attest` rather than folded into it the way the service path needs.

        THE SIGNATURE IS OVER THE TWO ROOTS, which are exactly what this CASes on and what the
        attestation will name -- so a host cannot pair a genuine signature with operands of its
        own choosing. It is checked against `ward_id`, which IS the verifying key, so there is no
        enrolment and no second per-wallet value.

        A wallet the WM has never seen has no head to compare against, so the first call must carry
        `head_init_sig` authorising the starting pair. Anyone could otherwise claim a wallet's
        opening head by being first to speak.
        """
        from .ward_keys import verify_head_init_sig, verify_wm_sig

        known = self._heads.get(ward_id)

        if known is None:
            if head_init_sig is None:
                raise ValueError("unknown ward_id and no head-init authorisation")
            if not verify_head_init_sig(
                ward_id, from_counter, from_root, head_init_sig
            ):
                raise ValueError("head-init authorisation does not verify")
            if from_counter != 0:
                raise ValueError("a wallet's first head must start at counter 0")
            # The opening head attests ITSELF -- genesis has no predecessor.
            self._heads[ward_id] = (
                from_counter,
                _or_empty(from_root),
                from_counter,
                _or_empty(from_root),
                timestamp,
            )
            known = self._heads[ward_id]

        # COMPARE-AND-SWAP. Refusing an advance from a head we do not hold is what stops two
        # devices both believing they wrote counter N.
        _phc, _phr, head_counter, head_root, _ts = known
        if (head_counter, head_root) != (from_counter, _or_empty(from_root)):
            raise MockWM.Conflict(head_counter)

        if to_counter != from_counter + 1:
            raise ValueError("a head advances by exactly one")

        # EITHER TAG, AND WHICH ONE IS THE POINT. A revert advances the head exactly like a
        # write -- forward one counter, carrying an OLDER root -- so the operands
        # cannot tell them apart. The tag can, and a real WM is where a policy on demotions
        # would live: rate-limit them, alert on them, require a second factor. This mock only
        # records the distinction, which is enough to prove the wire carries it.
        from .ward_keys import TAG_WM_HEAD, TAG_WM_REVERT

        if verify_wm_sig(
            ward_id, from_counter, from_root, to_counter, to_root, wm_sig, TAG_WM_HEAD
        ):
            is_revert = False
        elif verify_wm_sig(
            ward_id, from_counter, from_root, to_counter, to_root, wm_sig, TAG_WM_REVERT
        ):
            is_revert = True
        else:
            raise ValueError("transition is not authorised by this wallet")
        self.reverts_seen += int(is_revert)

        self._heads[ward_id] = (
            from_counter,
            _or_empty(from_root),
            to_counter,
            _or_empty(to_root),
            timestamp,
        )
        return is_revert

    def publish_and_attest(
        self,
        ward_id: bytes,
        nonce: bytes,
        from_counter: int,
        from_root: bytes,
        to_counter: int,
        to_root: bytes,
        wm_sig: bytes,
        timestamp: int,
        head_init_sig: Optional[bytes] = None,
    ) -> tuple:
        """`advance` then `attest`, as ONE operation. What the service path needs.

        Returns (from_counter, from_root, to_counter, to_root, timestamp, signature).

        ONE OPERATION, NOT TWO, and for the service path that is the point. Between a separate CAS
        and a separate attest another device can win: D1 advances 41->42, D2 advances 42->43, and
        D1's attest then describes 43 -- a head D1 did not publish. The device would reject it,
        having minted neither that counter nor that root, but its own write would already have
        landed with no way to learn so. Attesting the head THIS call created removes the window
        rather than detecting it afterwards.

        CONNECT MODE CANNOT USE IT, which is why `advance` exists on its own: there a write is
        published in one exchange and attested in a later sync round, so the window is real and is
        closed by the device comparing what came back against what it holds.
        """
        self.advance(
            ward_id,
            from_counter,
            from_root,
            to_counter,
            to_root,
            wm_sig,
            timestamp,
            head_init_sig,
        )
        return self.attest(ward_id, nonce)

    def attest_head(
        self,
        ward_id: bytes,
        nonce: bytes,
        current_counter: int,
        current_root: bytes,
        head_init_sig: bytes,
    ) -> tuple[int, bytes, int, bytes]:
        """Attest the current head, adopting the wallet's opening head if it is unknown.

        What a read-only first use needs: a device asks for the current head before it has ever
        written, so there may be nothing to attest yet. Same authorisation as above -- an opening
        head is a value anyone who knows `ward_id` could otherwise set.
        """
        from .ward_keys import verify_head_init_sig

        if ward_id not in self._heads:
            if not verify_head_init_sig(
                ward_id, current_counter, current_root, head_init_sig
            ):
                raise ValueError("head-init authorisation does not verify")
            # Attests itself: this is an opening head, not a step.
            self._heads[ward_id] = (
                current_counter,
                _or_empty(current_root),
                current_counter,
                _or_empty(current_root),
                0,
            )

        return self.attest(ward_id, nonce)

    def sign(
        self,
        ward_id: bytes,
        nonce: bytes,
        from_counter: int,
        from_root: "bytes | None",
        to_counter: int,
        to_root: "bytes | None",
        timestamp: int,
    ) -> bytes:
        """Sign arbitrary values -- used by tests that model a hostile or broken WM."""
        message = (
            _ATTEST_DOMAIN
            + bytes([_ATTEST_VERSION])
            + nonce
            + ward_id
            + from_counter.to_bytes(4, "big")
            + _or_empty(from_root)
            + to_counter.to_bytes(4, "big")
            + _or_empty(to_root)
            + timestamp.to_bytes(8, "big")
        )
        return _ed25519.signature_unsafe(message, self._seed, self._pub)
