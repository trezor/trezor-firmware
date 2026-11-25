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

"""The mock WM's compare-and-swap, tested on its own.

No device involved: this is the host half of the publish protocol, and the properties below are
what the firmware in Stage 3d will be relying on. Getting them wrong here would make a device
test fail for a reason that looks like a firmware bug.
"""

from __future__ import annotations

import pickle

import pytest

from trezorlib import _ed25519

from .ward_keys import TAG_WM_HEAD, head_init_sig, session_proof, wm_sig
from .ward_wm import MockWM

K_SIG = b"\x11" * 32
WARD_ID = _ed25519.publickey_unsafe(K_SIG)
ROOT_0 = b"\x00" * 31 + b"\x01"
ROOT_1 = b"\xaa" * 32
ROOT_2 = b"\xbb" * 32
NONCE = b"\x99" * 32


def _open(wm, nonce):
    proof = session_proof(K_SIG, WARD_ID, wm.challenge(WARD_ID), nonce)
    wm.open_session(WARD_ID, nonce, proof)
    return proof


def _sig(wm, frm, from_root, to, to_root, tag=TAG_WM_HEAD, k_sig=K_SIG):
    """The device's authorisation, bound to the session nonce of the WM's latest sync -- the round
    nonce the device picked, which it learns from the attestation it adopted."""
    return wm_sig(k_sig, WARD_ID, frm, from_root, to, to_root, tag, wm.session(WARD_ID) or b"")


def _advance(wm, frm, from_root, to, to_root, tag=None, **kw):
    sig = (
        _sig(wm, frm, from_root, to, to_root)
        if tag is None
        else _sig(wm, frm, from_root, to, to_root, tag)
    )
    return wm.publish_and_attest(
        WARD_ID, NONCE, frm, from_root, to, to_root, sig, timestamp=1000, **kw
    )


def _opened() -> MockWM:
    """A WM that has ENROLLED this wallet and taken one advance.

    TWO STEPS, NOT ONE, and that is the protocol rather than a quirk of the mock: the advance path
    cannot enrol. The firmware reaches this the same way -- a write needs an online session, and
    a session goes online by adopting an attestation.
    """
    wm = MockWM()
    wm.attest_head(WARD_ID, NONCE, 0, ROOT_0, head_init_sig(K_SIG, WARD_ID, 0, ROOT_0))
    _open(wm, NONCE)
    _advance(wm, 0, ROOT_0, 1, ROOT_1)
    return wm


def test_an_unenrolled_wallet_cannot_be_advanced_at_all():
    """ENROLMENT IS NOT AN ADVANCE, and cannot be folded into one.

    A compare-and-swap needs a head to compare against, and a WM that has never seen this wallet
    holds none. Enrolment is a SYNC-path operation: `attest_head` verifies `head_init_sig` and
    attests the genesis head; only then can a device authorise a write.

    The firmware reaches this shape on its own, because a write requires an online session and a
    session goes online by adopting an attestation.
    """
    wm = MockWM()
    with pytest.raises(ValueError, match="not enrolled"):
        _advance(wm, 0, ROOT_0, 1, ROOT_1)


def test_head_init_must_be_authorised():
    wm = MockWM()
    other = head_init_sig(b"\x22" * 32, WARD_ID, 0, ROOT_0)
    with pytest.raises(ValueError, match="head-init"):
        wm.attest_head(WARD_ID, NONCE, 0, ROOT_0, other)


def test_head_init_names_the_head_it_opens():
    """A signature over one opening head must not open a different one."""
    wm = MockWM()
    with pytest.raises(ValueError, match="head-init"):
        wm.attest_head(
            WARD_ID, NONCE, 0, ROOT_2, head_init_sig(K_SIG, WARD_ID, 0, ROOT_0)
        )


def test_a_first_head_starts_at_zero():
    """SIGNED FOR COUNTER 7, so the rule under test is the one that actually fires.

    The init signature names the counter it opens as well as the root, so offering a signature
    minted for counter 0 here would be refused as unauthorised and never reach this rule -- which
    is a strengthening rather than an obstacle, and worth having a test walk past deliberately.
    """
    wm = MockWM()
    with pytest.raises(ValueError, match="counter 0"):
        wm.attest_head(
            WARD_ID, NONCE, 7, ROOT_0, head_init_sig(K_SIG, WARD_ID, 7, ROOT_0)
        )


def test_an_advance_attests_the_head_it_created():
    """Not "the head now", which a concurrent winner could have moved -- the whole reason CAS and
    attestation are one call."""
    fc, fr, counter, root, ts, sig = _advance(_opened(), 1, ROOT_1, 2, ROOT_2)
    assert (fc, fr, counter, root, ts) == (1, ROOT_1, 2, ROOT_2, 1000)
    # THE WHOLE STEP IS SIGNED, both ends -- so an attestation cannot be paired with a link that
    # merely ends in the right place.
    _ed25519.checkvalid(
        sig,
        b"WARD ATTEST v1"
        + bytes([7])
        + NONCE
        + WARD_ID
        + (1).to_bytes(4, "big")
        + ROOT_1
        + (2).to_bytes(4, "big")
        + ROOT_2
        + (1000).to_bytes(8, "big"),
        MockWM().pubkey,
    )


def test_a_stale_predecessor_is_a_conflict_not_an_overwrite():
    """The device must be told it lost, so it can sync and retry, rather than have its transition
    silently replace the winner's."""
    wm = _opened()
    _advance(wm, 1, ROOT_1, 2, ROOT_2)
    with pytest.raises(MockWM.Conflict) as e:
        _advance(wm, 1, ROOT_1, 2, ROOT_0)
    assert e.value.head_counter == 2
    # ...and the head the winner installed is untouched
    assert wm.head(WARD_ID) == (2, ROOT_2, 1000)


def test_the_predecessor_root_is_compared_too():
    """Two forks can share a counter, so the counter alone does not identify a head."""
    wm = _opened()
    with pytest.raises(MockWM.Conflict):
        _advance(wm, 1, ROOT_2, 2, ROOT_2)


def test_a_head_advances_by_one_to_max_batch():
    """A batch is one transition carrying several changes; anything longer is refused."""
    from .ward_wm import MAX_BATCH

    too_far = _opened()
    with pytest.raises(ValueError, match="1 to MAX_BATCH"):
        _advance(too_far, 1, ROOT_1, 1 + MAX_BATCH + 1, ROOT_2)

    wm = _opened()
    _advance(wm, 1, ROOT_1, 1 + MAX_BATCH, ROOT_2)
    assert wm.head(WARD_ID)[:2] == (1 + MAX_BATCH, ROOT_2)


def test_an_unauthorised_transition_is_refused():
    """The WM verifies with `ward_id` alone -- no enrolment, and no second per-wallet secret."""
    wm = _opened()
    with pytest.raises(ValueError, match="not authorised"):
        wm.publish_and_attest(
            WARD_ID,
            NONCE,
            1,
            ROOT_1,
            2,
            ROOT_2,
            _sig(wm, 1, ROOT_1, 2, ROOT_2, k_sig=b"\x22" * 32),
            timestamp=1000,
        )
    assert wm.head(WARD_ID) == (1, ROOT_1, 1000)


def test_a_signature_for_another_transition_is_refused():
    wm = _opened()
    with pytest.raises(ValueError, match="not authorised"):
        wm.publish_and_attest(
            WARD_ID,
            NONCE,
            1,
            ROOT_1,
            2,
            ROOT_2,
            _sig(wm, 1, ROOT_1, 2, ROOT_0),
            timestamp=1000,
        )


def test_a_read_only_first_use_can_attest_without_publishing():
    """A read may be a wallet's first WARD operation, so the WM has to be able to bootstrap from
    an attestation request rather than only from a write."""
    wm = MockWM()
    fc, fr, counter, root, _ts, _sig = wm.attest_head(
        WARD_ID, NONCE, 0, ROOT_0, head_init_sig(K_SIG, WARD_ID, 0, ROOT_0)
    )
    # AN OPENING HEAD ATTESTS ITSELF: no step produced it, so naming one would be inventing a
    # transition that never happened.
    assert (fc, fr, counter, root) == (0, ROOT_0, 0, ROOT_0)
    _open(wm, NONCE)
    # and the head it adopted is now the one an advance must build on
    _advance(wm, 0, ROOT_0, 1, ROOT_1)
    assert wm.head(WARD_ID)[:2] == (1, ROOT_1)


def test_enrolment_is_genesis_only():
    """A WM MAY BE ENROLLED AT COUNTER 0 AND NOWHERE ELSE.

    `head_init_sig` proves the head it names was a genuine state of this wallet. It does not
    prove that head is the LATEST one, and no signature one device can produce ever could --
    every device holds an authentic one over its own head, and they disagree whenever one is
    behind. So enrolling at an arbitrary counter would hand whichever device reached an empty WM
    first the power to pin the head to older state, and refuse the others against it from then on.

    THE FIRMWARE ENFORCES THE OTHER HALF, which is what makes this more than a policy choice: an
    attestation may only be a self-transition at counter 0 (`adopt.verify_round_attestation`), so
    a WM that enrolled at 57 would install `57 -> 57` and emit attestations no device can accept.

    RE-SEEDING A WM THAT LOST ITS REGISTER is therefore not this, and is deliberately absent. It
    needs the WM's persisted head restored, or a named recovery operation with a policy for which
    device's claim wins.
    """
    from .ward_keys import head_init_sig as _init

    at57 = _init(K_SIG, WARD_ID, 57, ROOT_1)

    wm = MockWM()
    with pytest.raises(ValueError, match="counter 0"):
        wm.attest_head(WARD_ID, NONCE, 57, ROOT_1, at57)

    # ...and the advance path cannot enrol at ALL any more, at any counter -- see
    # `test_an_unenrolled_wallet_cannot_be_advanced_at_all`. So there is one enrolment entry
    # point and one rule on it, rather than two paths that had to be kept agreeing.
    wm2 = MockWM()
    with pytest.raises(ValueError, match="not enrolled"):
        _advance(wm2, 57, ROOT_1, 58, ROOT_2)

    # Genesis still enrols, which is the case that has to keep working.
    wm3 = MockWM()
    fc, fr, tc, tr, _ts, _sig = wm3.attest_head(
        WARD_ID, NONCE, 0, ROOT_0, head_init_sig(K_SIG, WARD_ID, 0, ROOT_0)
    )
    assert (fc, fr, tc, tr) == (0, ROOT_0, 0, ROOT_0)


def test_a_read_only_bootstrap_is_authorised_too():
    wm = MockWM()
    with pytest.raises(ValueError, match="head-init"):
        wm.attest_head(
            WARD_ID, NONCE, 0, ROOT_0, head_init_sig(b"\x22" * 32, WARD_ID, 0, ROOT_0)
        )


def test_a_revert_is_authorised_but_distinguishable():
    """The WM accepts a demotion and can TELL it was one.

    A revert advances the head exactly like a write -- forward one counter, carrying an OLDER
    root -- so nothing in the operands separates them. Only the tag does, which is why
    it exists: a WM that could not distinguish them could not apply policy to demotions.
    """
    from .ward_keys import TAG_WM_REVERT

    wm = _opened()
    assert wm.reverts_seen == 0

    _advance(wm, 1, ROOT_1, 2, ROOT_2, tag=TAG_WM_REVERT)

    assert wm.reverts_seen == 1
    assert wm.head(WARD_ID)[:2] == (2, ROOT_2)


def test_a_revert_signature_is_not_accepted_as_an_ordinary_advance():
    """The two tags are not interchangeable in either direction.

    Sharing one would let a demotion be replayed as a write, or a write drive a rollback.
    """
    from .ward_keys import TAG_WM_REVERT, verify_wm_sig

    revert = wm_sig(K_SIG, WARD_ID, 1, ROOT_1, 2, ROOT_2, TAG_WM_REVERT)
    ordinary = wm_sig(K_SIG, WARD_ID, 1, ROOT_1, 2, ROOT_2)
    assert revert != ordinary

    # each verifies only under its own tag
    assert verify_wm_sig(WARD_ID, 1, ROOT_1, 2, ROOT_2, revert, TAG_WM_REVERT)
    assert not verify_wm_sig(WARD_ID, 1, ROOT_1, 2, ROOT_2, revert)
    assert verify_wm_sig(WARD_ID, 1, ROOT_1, 2, ROOT_2, ordinary)
    assert not verify_wm_sig(WARD_ID, 1, ROOT_1, 2, ROOT_2, ordinary, TAG_WM_REVERT)


def test_an_authorisation_moves_the_head_at_most_once():
    """THE COMPARE-AND-SWAP, stated as the attack it closes.

    A host that kept a `wm_sig` waits for its predecessor to come back. Roots do come back -- a
    tree returning to an earlier shape returns to an earlier root, and a REVERT carries an older
    root forward on purpose -- but always under a higher counter, because every accepted
    transition raises it. The kept authorisation names a predecessor counter the WM has passed.
    """
    wm = _opened()
    kept = _sig(wm, 1, ROOT_1, 2, ROOT_2)

    # it works exactly once
    wm.advance(WARD_ID, 1, ROOT_1, 2, ROOT_2, kept, timestamp=1000)

    # the ROOT comes back, under counter 3; the kept authorisation is still refused
    _advance(wm, 2, ROOT_2, 3, ROOT_1)
    assert wm.head(WARD_ID)[:2] == (3, ROOT_1)
    with pytest.raises(MockWM.Conflict):
        wm.advance(WARD_ID, 1, ROOT_1, 2, ROOT_2, kept, timestamp=1000)


# --- sessions -------------------------------------------------------------------------------


def test_one_session_carries_several_transitions():
    """The session is the device's sync, not the head: it survives the head moving."""
    wm = _opened()
    session = wm.session(WARD_ID)
    for frm, fr, to, tr in [(1, ROOT_1, 2, ROOT_2), (2, ROOT_2, 3, ROOT_0)]:
        wm.advance(WARD_ID, frm, fr, to, tr, _sig(wm, frm, fr, to, tr), timestamp=1000)
    assert wm.head(WARD_ID)[:2] == (3, ROOT_0)
    assert wm.session(WARD_ID) == session


def test_a_new_sync_ends_the_session():
    """An authorisation minted in one sync is refused once any device of the wallet syncs again:
    a lost race, or a write a host held back, does not land later."""
    wm = _opened()
    held_back = _sig(wm, 1, ROOT_1, 2, ROOT_2)
    _open(wm, b"\x42" * 32)  # another sync, another nonce the device picked
    with pytest.raises(ValueError, match="not authorised"):
        wm.advance(WARD_ID, 1, ROOT_1, 2, ROOT_2, held_back, timestamp=1000)


def test_only_a_fresh_device_proof_can_replace_the_write_session():
    """Reads and consumed opening proofs preserve the current write session. A host that asks for
    an attestation under an old nonce, or replays that nonce's opening proof, cannot make the
    held write land: the proof's challenge was consumed when the session opened."""
    wm = _opened()
    old = b"A" * 32
    proof = _open(wm, old)
    held = _sig(wm, 1, ROOT_1, 2, ROOT_2)
    current = b"B" * 32
    _open(wm, current)
    wm.attest(WARD_ID, old)
    with pytest.raises(ValueError, match="expired"):
        wm.open_session(WARD_ID, old, proof)
    assert wm.session(WARD_ID) == current
    with pytest.raises(ValueError, match="not authorised"):
        wm.advance(WARD_ID, 1, ROOT_1, 2, ROOT_2, held, timestamp=1000)


def test_restarting_the_python_service_discards_its_session_and_pending_challenge():
    """A restart starts with no session and a fresh challenge, so a proof minted before it does
    not open a session after it."""
    wm = _opened()
    candidate = b"C" * 32
    proof = session_proof(K_SIG, WARD_ID, wm.challenge(WARD_ID), candidate)
    restarted = pickle.loads(pickle.dumps(wm))
    assert restarted.record(WARD_ID) == wm.record(WARD_ID)
    assert restarted.session(WARD_ID) is None
    with pytest.raises(ValueError, match="expired"):
        restarted.open_session(WARD_ID, candidate, proof)


def test_an_advance_returns_the_wm_signed_acceptance():
    """The WM's own record of the transition, under the session nonce: what roll-forward takes."""
    wm = _opened()
    session = wm.session(WARD_ID)
    wm.advance(WARD_ID, 1, ROOT_1, 2, ROOT_2, _sig(wm, 1, ROOT_1, 2, ROOT_2), timestamp=1000)
    fc, fr, tc, tr, ts, sig = wm.last_acceptance
    assert (fc, fr, tc, tr, ts) == (1, ROOT_1, 2, ROOT_2, 1000)
    assert wm.acceptance(WARD_ID, 1, ROOT_1, 2, ROOT_2).nonce == session
    _ed25519.checkvalid(
        sig,
        b"WARD ATTEST v1"
        + bytes([7])
        + session
        + WARD_ID
        + (1).to_bytes(4, "big")
        + ROOT_1
        + (2).to_bytes(4, "big")
        + ROOT_2
        + (1000).to_bytes(8, "big"),
        wm.pubkey,
    )


# --- a register that goes back ---------------------------------------------------------------
#
# A restored backup, a failover onto a stale replica, a re-enrolment after total loss. The session
# nonce does not come back with it, so no device authorisation minted before is accepted. What the
# WM had accepted comes back by ROLL-FORWARD: a device checks each step's auth_commit and the WM's
# record of it, and signs it again for the session now current (`WardRollForward`, tested on the
# device). Here the oracle stands in for that device. Whoever holds the records still decides where
# the replay stops. See docs/ward/ward_transitions.md.


def _history(wm):
    """Three accepted steps after `_opened`, returning each step and the WM's record of it."""
    steps = [(1, ROOT_1, 2, ROOT_2), (2, ROOT_2, 3, ROOT_0), (3, ROOT_0, 4, ROOT_1)]
    records = []
    for step in steps:
        wm.advance(WARD_ID, *step, _sig(wm, *step), timestamp=1000)
        records.append((step, wm.acceptance(WARD_ID, *step)))
    return records


def _re_sign(wm, step, timestamp=1100):
    """What `WardRollForward` hands back: the step signed again, for the current session."""
    wm.advance(WARD_ID, *step, _sig(wm, *step), timestamp=timestamp)


def test_a_restored_wm_is_rolled_forward_by_steps_signed_again():
    wm = _opened()
    records = _history(wm)
    assert all(record is not None for _step, record in records)
    assert wm.head(WARD_ID)[:2] == (4, ROOT_1)

    wm.restore_backup(WARD_ID, 1, ROOT_1, 900)
    assert wm.head(WARD_ID)[:2] == (1, ROOT_1)
    _open(wm, b"\x77" * 32)  # the device's sync opens the session the replay runs in
    for step, _record in records:
        _re_sign(wm, step)
    assert wm.head(WARD_ID)[:2] == (4, ROOT_1)


def test_a_restored_wm_refuses_the_devices_authorisations():
    """The session nonce is volatile, so a restore ends every session: the device signatures a
    host kept are refused, accepted ones and lost races alike -- also after a new sync."""
    wm = _opened()
    kept = _sig(wm, 1, ROOT_1, 2, ROOT_2)
    wm.advance(WARD_ID, 1, ROOT_1, 2, ROOT_2, kept, timestamp=1000)
    wm.restore_backup(WARD_ID, 1, ROOT_1, 900)
    with pytest.raises(ValueError, match="no session"):
        wm.advance(WARD_ID, 1, ROOT_1, 2, ROOT_2, kept, timestamp=1000)
    _open(wm, b"\x77" * 32)
    with pytest.raises(ValueError, match="not authorised"):
        wm.advance(WARD_ID, 1, ROOT_1, 2, ROOT_2, kept, timestamp=1000)


def test_a_lost_race_has_no_record_to_be_signed_again_from():
    """Two devices mint from the same head; one lands. The loser has a device signature but no WM
    record, so a device will not sign it again, and its own signature is refused."""
    wm = _opened()
    loser = _sig(wm, 1, ROOT_1, 2, ROOT_0)
    wm.advance(WARD_ID, 1, ROOT_1, 2, ROOT_2, _sig(wm, 1, ROOT_1, 2, ROOT_2), timestamp=1000)
    wm.restore_backup(WARD_ID, 1, ROOT_1, 900)

    assert wm.acceptance(WARD_ID, 1, ROOT_1, 2, ROOT_0) is None
    assert wm.acceptance(WARD_ID, 1, ROOT_1, 2, ROOT_2) is not None
    _open(wm, b"\x77" * 32)
    with pytest.raises(ValueError, match="not authorised"):
        wm.advance(WARD_ID, 1, ROOT_1, 2, ROOT_0, loser, timestamp=1000)


def test_a_stale_session_named_for_diagnostics_explains_the_refusal():
    """The host may say which session it believes is current. The WM verifies against its own
    nonce regardless; a stale one named only changes the reason it gives."""
    wm = _opened()
    old = wm.session(WARD_ID)
    held = _sig(wm, 1, ROOT_1, 2, ROOT_2)
    _open(wm, b"\x42" * 32)
    with pytest.raises(ValueError, match="the session it names has ended"):
        wm.advance(WARD_ID, 1, ROOT_1, 2, ROOT_2, held, timestamp=1000, session=old)
    # naming the right session does not make a bad signature good
    with pytest.raises(ValueError, match="not authorised"):
        wm.advance(
            WARD_ID, 1, ROOT_1, 2, ROOT_2, bytes(64), timestamp=1000, session=wm.session(WARD_ID)
        )


def test_a_restored_wm_can_be_stopped_at_any_prefix():
    """THE COST that remains: whoever holds the records decides where the replay stops. The WM
    then attests an older genuine head as current; only devices whose stored counter is already
    past it refuse it. Accepted gap: see "WM restore and roll-forward" in docs/ward/gaps.md."""
    wm = _opened()
    records = _history(wm)
    wm.restore_backup(WARD_ID, 1, ROOT_1, 900)
    _open(wm, b"\x77" * 32)
    _re_sign(wm, records[0][0])
    assert wm.head(WARD_ID)[:2] == (2, ROOT_2)  # not 4, and nothing on the WM says so


def test_a_re_enrolled_wm_refuses_a_kept_first_write():
    """`head_init_sig` is not secret, so a WM that lost everything can be enrolled again at
    genesis. The first write's device signature belonged to a session that is gone."""
    init = head_init_sig(K_SIG, WARD_ID, 0, ROOT_0)
    wm = MockWM()
    wm.attest_head(WARD_ID, NONCE, 0, ROOT_0, init)
    _open(wm, NONCE)
    first_write = _sig(wm, 0, ROOT_0, 1, ROOT_1)
    wm.advance(WARD_ID, 0, ROOT_0, 1, ROOT_1, first_write, timestamp=1000)

    reborn = MockWM()
    reborn.attest_head(WARD_ID, b"\x43" * 32, 0, ROOT_0, init)
    _open(reborn, b"C" * 32)
    with pytest.raises(ValueError, match="not authorised"):
        reborn.advance(WARD_ID, 0, ROOT_0, 1, ROOT_1, first_write, timestamp=1000)


# --- the named scenarios --------------------------------------------------------------------------


def test_a_failover_takes_the_record_as_it_stands():
    primary = _opened()
    record = primary.record(WARD_ID)
    standby = MockWM()
    standby.take_over(WARD_ID, record)
    assert standby.record(WARD_ID) == record
    # sessions do not fail over: the device syncs with the standby before it writes
    assert standby.session(WARD_ID) is None
    _open(standby, b"S" * 32)
    _advance(standby, 1, ROOT_1, 2, ROOT_2)
    assert standby.head(WARD_ID)[:2] == (2, ROOT_2)


def test_a_restore_onto_the_current_head_changes_nothing_visible():
    wm = _opened()
    held = wm.record(WARD_ID)
    wm.restore_backup(WARD_ID, 1, ROOT_1, 1000)
    assert wm.record(WARD_ID) == held


def test_a_lost_wallet_can_only_come_back_at_genesis():
    wm = _opened()
    wm.lose_wallet(WARD_ID)
    assert wm.head(WARD_ID) is None and wm.record(WARD_ID) is None

    with pytest.raises(ValueError, match="counter 0"):
        wm.attest_head(
            WARD_ID, NONCE, 1, ROOT_1, head_init_sig(K_SIG, WARD_ID, 1, ROOT_1)
        )
    wm.attest_head(WARD_ID, NONCE, 0, ROOT_0, head_init_sig(K_SIG, WARD_ID, 0, ROOT_0))
    assert wm.head(WARD_ID)[:2] == (0, ROOT_0)
