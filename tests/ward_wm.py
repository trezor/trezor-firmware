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
of it. It already checks the predecessor against the `from` end, so the value was always in hand --
this just keeps it.

IT SEES ROOTS, AND THAT IS A DELIBERATE NARROWING OF WHAT IT USED TO BE. The head was once a
`root_mac` under a device-only K_mac, so the WM signed a value it could not compute and was
therefore bounded to replaying states the wallet genuinely reached. That key is gone. This mock
holds `(counter, root)` and can trivially invent one -- and a test that wants to model a hostile
WM should. What refuses an invented root is the DEVICE, which folds an `auth_commit` into every
adoption; minting one needs K_auth, which this file has no access to and must never acquire.

It still sees no identifier and no value: it is told roots, never leaves.
"""

from __future__ import annotations

from secrets import token_bytes
from typing import NamedTuple, Optional

from trezorlib import _ed25519

__all__ = ["MockWM", "WMRecord", "DEBUG_WM_SEED"]

# The well-known debug WM key. Firmware compiles in its public key and accepts it on
# debug builds only; a release build ships an all-zero placeholder and rejects everything.
DEBUG_WM_SEED = b"AUTHDB QM DEBUG KEY SEED v1 ...."

_ATTEST_DOMAIN = b"WARD ATTEST v1"
# 3: the 32-byte field became the ROOT rather than a mac over it. 4: the preimage names a
# TRANSITION rather than a single head, so both ends travel. 5 and 6 carried the WM's head
# nonce. 7: the head nonce is gone; a transition is named by its (counter, root) ends.
_ATTEST_VERSION = 7

# The empty tree's stand-in inside a preimage, mirroring apps.ward.attest.EMPTY_ROOT. A head can
# legitimately BE the empty tree -- counter 0, and any wallet drained back to nothing -- so every
# entry point here normalises rather than assuming a root is present.
import hashlib as _hashlib

EMPTY_ROOT = _hashlib.sha256(b"\x02").digest()


def _or_empty(root):
    return root if root is not None else EMPTY_ROOT


# Mirrors `apps.ward.transition.MAX_BATCH`: the most changes one transition may carry.
MAX_BATCH = 8


# --- SESSIONS, AND WHAT A RESTORE MAY BRING BACK ------------------------------------------
#
# A device's `wm_sig` is bound to the SESSION NONCE: the round nonce it picked for its latest sync,
# which this WM's attestation answered. The WM never picks one. It keeps the nonce of each
# wallet's latest sync, replaces it on the next sync (by any device of the wallet), and accepts an
# authorisation only when it is bound to that nonce and its predecessor is the head (the
# predecessor check). One session can carry several transitions.
#
# THE SESSION NONCE IS VOLATILE: a restore, failover or lost wallet drops it. So a restored WM does
# not take the authorisations devices minted before -- a lost race, a write held back. What it
# had ACCEPTED comes back by ROLL-FORWARD: a host feeds a device the transitions with this WM's
# signed record of each, and the device signs them again for the current session
# (`WardRollForward`); they then arrive here as ordinary advances. Whoever holds the records still
# chooses where the replay stops; see docs/ward/ward_transitions.md.


class WMRecord(NamedTuple):
    """One wallet's register row: the step that reached the head. It holds no time: the WM signs
    each attestation with its clock at signing, and wardd keeps the signed records."""

    from_counter: int
    from_root: bytes
    counter: int
    root: bytes


class MockWM:
    """The freshness authority. Knows counters and roots; knows nothing about leaves."""

    def __init__(self, seed: bytes = DEBUG_WM_SEED) -> None:
        self._seed = seed
        self._pub = _ed25519.publickey_unsafe(seed)
        # How many demotions this WM has been asked to accept. A real one would apply policy
        # here; recording it is how a test shows the REVERT tag actually reached the WM.
        self.reverts_seen = 0
        # ward_id -> (from_counter, from_root, to_counter, to_root). An absent root is the empty
        # tree and is held as EMPTY_ROOT, the form it takes inside the preimage.
        self._heads: dict[bytes, tuple[int, bytes, int, bytes]] = {}
        # ward_id -> the WM's clock as the test last set it. NOT REGISTER STATE: a real WM reads
        # its own clock whenever it signs, and its register holds no time. The `timestamp` that
        # scenarios and `advance` take sets this clock, so a test controls what the next
        # attestation says.
        self._clock: dict[bytes, int] = {}
        # (ward_id, from_counter, from_root, to_counter, to_root) -> (round nonce, attestation):
        # the newest attestation of each step, which wardd keeps and serves to WardRollback.
        self._accepted: dict[tuple, tuple] = {}
        # ward_id -> the round nonce of that wallet's latest sync. Volatile: never in a record.
        self._session: dict[bytes, bytes] = {}
        self._initial_challenge = token_bytes(32)
        self._challenges: dict[bytes, bytes] = {}

    def __getstate__(self):
        # The Python service fixture pickles its WM together with the replica.
        state = vars(self).copy()
        for key in ("_session", "_initial_challenge", "_challenges"):
            state.pop(key)
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._session = {}
        self._initial_challenge = token_bytes(32)
        self._challenges = {}

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

        A real WM takes its head from `advance`, which checks the predecessor and verifies `wm_sig`.
        This exists only to model a WM that has been told something by a party holding no
        signature -- a broken operator, a fixture standing in for history that predates the test,
        a hostile WM inventing state, or a register rebuilt from a backup.

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
        self._heads[ward_id] = (from_counter, _or_empty(from_root), counter, _or_empty(root))
        self._clock[ward_id] = timestamp

    # --- NAMED SCENARIOS --------------------------------------------------------------------
    #
    # What happens to a real WM's register, each as the operation it is. They are all built on
    # `install_unauthenticated` -- none is an authorised advance -- and exist so a test reads as
    # the incident it models.

    def record(self, ward_id: bytes) -> "Optional[WMRecord]":
        """The register row for a wallet, as an operator would back it up or hand to a standby."""
        known = self._heads.get(ward_id)
        return None if known is None else WMRecord(*known)

    def force_head(
        self,
        ward_id: bytes,
        counter: int,
        root: bytes,
        timestamp: int,
        from_counter: "int | None" = None,
        from_root: "bytes | None" = None,
    ) -> None:
        """FIXTURE: stand in for history made before the test, or by a writer the test elides."""
        self.install_unauthenticated(
            ward_id, counter, root, timestamp, from_counter, from_root
        )

    def restore_backup(
        self,
        ward_id: bytes,
        counter: int,
        root: bytes,
        timestamp: int,
        from_counter: "int | None" = None,
        from_root: "bytes | None" = None,
    ) -> None:
        """DISASTER RECOVERY: the register is rebuilt from a backup taken at `(counter, root)`.

        The counter and the root may go BACKWARDS -- that is what a restore is, and it is the one
        case where a `(counter, root)` pair this WM already passed becomes current again. The
        predecessor is the step this WM archived into that head, when it has one.
        """
        archived_step = next(
            (
                answer
                for (wallet, *_), (_, answer) in reversed(list(self._accepted.items()))
                if wallet == ward_id
                and (answer[2], answer[3]) == (counter, _or_empty(root))
                and (
                    from_counter is None
                    or answer[:2] == (from_counter, _or_empty(from_root))
                )
            ),
            None,
        )
        if archived_step is not None:
            from_counter, from_root = archived_step[:2]
        self.install_unauthenticated(
            ward_id, counter, root, timestamp, from_counter, from_root
        )
        # the session nonce is volatile: a rebuilt register does not have it
        self._session.pop(ward_id, None)
        self._challenges[ward_id] = token_bytes(32)

    def take_over(self, ward_id: bytes, record: "WMRecord", now: int = 0) -> None:
        """A FAILOVER: this standby takes the primary's record as it stands, and signs with its
        own clock (`now`). Sessions do not fail over; devices sync with the standby first."""
        self._session.pop(ward_id, None)
        self._challenges[ward_id] = token_bytes(32)
        self.install_unauthenticated(
            ward_id,
            record.counter,
            record.root,
            now,
            record.from_counter,
            record.from_root,
        )

    def lose_wallet(self, ward_id: bytes) -> None:
        """TOTAL LOSS of one wallet's register. It can come back only by enrolling at genesis."""
        self._heads.pop(ward_id, None)
        self._session.pop(ward_id, None)
        self._challenges[ward_id] = token_bytes(32)

    def set_clock(self, ward_id: bytes, now: int) -> None:
        """Time passes at the WM: its next signature for this wallet is dated `now`."""
        self._clock[ward_id] = now

    def head(self, ward_id: bytes) -> Optional[tuple[int, bytes]]:
        """The HEAD -- `(counter, root)` -- not the step that reached it."""
        known = self._heads.get(ward_id)
        if known is None:
            return None
        _fc, _fr, counter, root = known
        return counter, root

    def step(self, ward_id: bytes) -> Optional[tuple]:
        """(from_counter, from_root, to_counter, to_root)."""
        return self._heads.get(ward_id)

    def challenge(self, ward_id: bytes) -> bytes:
        return self._challenges.get(ward_id, self._initial_challenge)

    def open_session(self, ward_id: bytes, nonce: bytes, proof: bytes) -> tuple:
        if ward_id not in self._heads:
            raise ValueError("wallet is not enrolled")
        if len(nonce) != 32 or not proof or len(proof) != 64:
            raise ValueError("invalid session proof")
        try:
            _ed25519.checkvalid(
                proof,
                b"WARD SESSION OPEN v1" + ward_id + self.challenge(ward_id) + nonce,
                ward_id,
            )
        except Exception as exc:
            raise ValueError("invalid or expired session proof") from exc
        answer = self.attest(ward_id, nonce)
        self._challenges[ward_id] = token_bytes(32)
        self._session[ward_id] = nonce
        return answer

    def attest(self, ward_id: bytes, nonce: bytes) -> tuple:
        """Read the head without opening or changing the write session."""
        return self._sign_step(ward_id, nonce)

    def session(self, ward_id: bytes) -> Optional[bytes]:
        """The wallet's session nonce: the round nonce of its latest sync, or None."""
        return self._session.get(ward_id)

    def _sign_step(self, ward_id: bytes, nonce: bytes) -> tuple:
        """Sign the step into the current head against `nonce`, at the WM's clock, and archive it:
        the archive stands in for the records wardd keeps."""
        fc, fr, counter, root = self._heads[ward_id]
        timestamp = self._clock.get(ward_id, 0)
        answer = (
            fc,
            fr,
            counter,
            root,
            timestamp,
            self.sign(ward_id, nonce, fc, fr, counter, root, timestamp),
        )
        self._accepted[ward_id, fc, fr, counter, root] = (nonce, answer)
        return answer

    def acceptance(self, ward_id: bytes, from_counter, from_root, to_counter, to_root):
        """The archived WM attestation of one step, as WardRollback wants it, or None."""
        from trezorlib import messages

        archived = self._accepted.get(
            (ward_id, from_counter, _or_empty(from_root), to_counter, _or_empty(to_root))
        )
        if archived is None:
            return None
        nonce, (_fc, _fr, _tc, _tr, ts, sig) = archived
        return messages.WardChainAcceptance(nonce=nonce, timestamp=ts, wm_signature=sig)

    def acceptance_source(self, ward_id: bytes):
        """`trezorlib.ward.AcceptanceSource` over this WM's archive."""
        return lambda fc, fr, tc, tr: self.acceptance(ward_id, fc, fr, tc, tr)

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
        session: "bytes | None" = None,
    ) -> bool:
        """Check the predecessor, verify the wallet's authorisation, advance the head. Returns
        is_revert.

        `session` is what the host believes the session nonce is. DIAGNOSTICS ONLY: the signature
        is verified against the nonce this WM holds, and `session` only explains a refusal.

        THE AUTHENTICATED WAY IN, and the only one a real host has. THE SIGNATURE IS OVER THE TWO
        ROOTS, which are exactly what this checks the predecessor against and what the attestation
        will name -- so a host cannot pair a genuine signature with operands of its own choosing.
        It is checked against
        `ward_id`, which IS the verifying key, so there is no enrolment and no second per-wallet
        value.

        BOUND TO THE SESSION. The signature must cover the nonce of the wallet's latest sync, which
        this WM holds; a new sync ends the session. The WM signs its acceptance under that same
        nonce -- the record `replay` takes after a restore.

        IT DOES NOT ENROL. Enrolment happens on the SYNC path (`attest_head`), which is where
        `head_init_sig` is verified.
        """
        from .ward_keys import TAG_WM_HEAD, TAG_WM_REVERT, verify_wm_sig

        known = self._heads.get(ward_id)
        if known is None:
            raise ValueError("wallet is not enrolled with this WM; sync first")

        # PREDECESSOR CHECK. Refusing an advance from a head we do not hold is what stops two
        # devices both believing they wrote counter N, and -- because the counter only rises --
        # what stops one authorisation landing twice.
        _phc, _phr, head_counter, head_root = known
        if (head_counter, head_root) != (from_counter, _or_empty(from_root)):
            raise MockWM.Conflict(head_counter)

        # FORWARD, by the number of changes the transition carries: one for a write, up to
        # MAX_BATCH for a batch of queued changes.
        if not 1 <= to_counter - from_counter <= MAX_BATCH:
            raise ValueError("a head advances by 1 to MAX_BATCH")

        # EITHER TAG, AND WHICH ONE IS THE POINT. A revert advances the head exactly like a
        # write -- forward, carrying an OLDER root -- so the operands cannot tell them apart. The
        # tag can, and a real WM is where a policy on demotions would live.
        ops = (ward_id, from_counter, from_root, to_counter, to_root, wm_sig)
        claimed = session
        session = self._session.get(ward_id)
        if session is None:
            raise ValueError("no session for this wallet; sync first")
        if verify_wm_sig(*ops, TAG_WM_HEAD, session):
            is_revert = False
        elif verify_wm_sig(*ops, TAG_WM_REVERT, session):
            is_revert = True
        elif claimed is not None and claimed != session:
            raise ValueError(
                "transition is not authorised by this wallet: the session it names has ended"
            )
        else:
            raise ValueError("transition is not authorised by this wallet")
        self.reverts_seen += int(is_revert)

        self._heads[ward_id] = (
            from_counter,
            _or_empty(from_root),
            to_counter,
            _or_empty(to_root),
        )
        # `timestamp` is the WM's clock now: the acceptance is signed at it, the register keeps none
        self._clock[ward_id] = timestamp
        # THE ACCEPTANCE, signed under the session nonce: this WM's own record of the transition
        self.last_acceptance = self._sign_step(ward_id, session)
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
    ) -> tuple:
        """`advance` then `attest`, as ONE operation. What the service path needs.

        Returns (from_counter, from_root, to_counter, to_root, timestamp, signature).

        ONE OPERATION, NOT TWO: between a separate predecessor check and a separate attest another
        device can win, and the attest would then describe a head this caller did not publish.
        """
        self.advance(
            ward_id,
            from_counter,
            from_root,
            to_counter,
            to_root,
            wm_sig,
            timestamp,
        )
        return self.attest(ward_id, nonce)

    def attest_head(
        self,
        ward_id: bytes,
        nonce: bytes,
        current_counter: int,
        current_root: bytes,
        head_init_sig: bytes,
    ) -> tuple:
        """Attest the current head, ENROLLING the wallet at genesis if it is unknown.

        GENESIS ONLY. A `head_init_sig` proves the named head was a GENUINE STATE OF THIS WALLET;
        it does not prove it is the LATEST one. At counter 0 there is nothing to choose between,
        so enrolment is safe exactly there and nowhere else.
        """
        from .ward_keys import verify_head_init_sig

        if ward_id not in self._heads:
            if current_counter != 0:
                raise ValueError(
                    "a wallet's first head must start at counter 0; a WM that lost its "
                    "register cannot be re-seeded from a device's current head"
                )
            if not verify_head_init_sig(
                ward_id, current_counter, current_root, head_init_sig
            ):
                raise ValueError("head-init authorisation does not verify")
            self._heads[ward_id] = (
                current_counter,
                _or_empty(current_root),
                current_counter,
                _or_empty(current_root),
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
        message = self._preimage(
            ward_id, nonce, from_counter, from_root, to_counter, to_root, timestamp
        )
        return _ed25519.signature_unsafe(message, self._seed, self._pub)

    @staticmethod
    def _preimage(ward_id, nonce, from_counter, from_root, to_counter, to_root, timestamp):
        return (
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
