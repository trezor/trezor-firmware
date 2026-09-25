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

import pytest

from trezorlib import _ed25519

from .ward_keys import head_init_sig, wm_sig
from .ward_wm import NO_HEAD_NONCE, MockWM

K_SIG = b"\x11" * 32
WARD_ID = _ed25519.publickey_unsafe(K_SIG)
ROOT_0 = b"\x00" * 31 + b"\x01"
ROOT_1 = b"\xaa" * 32
ROOT_2 = b"\xbb" * 32
NONCE = b"\x99" * 32


def _advance(wm, frm, from_root, to, to_root, tag=None, **kw):
    # THE NONCE THE WM CURRENTLY HOLDS. A real device learns it from the WM's last attestation;
    # here the test reads it off the WM directly, which is the same value by construction and
    # keeps this file about the WM's own rules rather than about the sync round.
    nonce = wm.head_nonce(WARD_ID)
    sig = (
        wm_sig(K_SIG, WARD_ID, frm, from_root, to, to_root, nonce)
        if tag is None
        else wm_sig(K_SIG, WARD_ID, frm, from_root, to, to_root, nonce, tag)
    )
    return wm.publish_and_attest(
        WARD_ID, NONCE, frm, from_root, to, to_root, sig, timestamp=1000, **kw
    )


def _opened() -> MockWM:
    """A WM that has ENROLLED this wallet and taken one advance.

    TWO STEPS, NOT ONE, and that is the protocol rather than a quirk of the mock: enrolment is
    what makes the WM draw `N0`, and an authorisation has to quote `N0`, so nothing can be
    authorised until the enrolment has been accepted and attested. The firmware reaches this the
    same way -- a write needs an online session, and a session goes online by adopting an
    attestation.
    """
    wm = MockWM()
    wm.attest_head(WARD_ID, NONCE, 0, ROOT_0, head_init_sig(K_SIG, WARD_ID, 0, ROOT_0))
    _advance(wm, 0, ROOT_0, 1, ROOT_1)
    return wm


def test_an_unenrolled_wallet_cannot_be_advanced_at_all():
    """ENROLMENT IS NOT AN ADVANCE, and cannot be folded into one.

    An authorisation must quote the nonce the WM currently holds, and a WM that has never seen
    this wallet holds none -- so there is no signature a device could present here that would be
    checkable against anything. Enrolment is a SYNC-path operation: `attest_head` verifies
    `head_init_sig`, draws `N0`, and attests it; only then can a device authorise a write.

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
    fc, fr, fhn, counter, root, hn, ts, sig = _advance(_opened(), 1, ROOT_1, 2, ROOT_2)
    assert (fc, fr, counter, root, ts) == (1, ROOT_1, 2, ROOT_2, 1000)
    # THE WHOLE STEP IS SIGNED, both ends -- so an attestation cannot be paired with a link that
    # merely ends in the right place.
    _ed25519.checkvalid(
        sig,
        b"WARD ATTEST v1"
        + bytes([6])
        + NONCE
        + WARD_ID
        + (1).to_bytes(4, "big")
        + ROOT_1
        # THE NONCE THIS STEP CONSUMED, which is what names the occurrence...
        + fhn
        + (2).to_bytes(4, "big")
        + ROOT_2
        # ...and the one it minted, travelling back so the device can quote it in its NEXT
        # authorisation.
        + hn
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


def test_a_head_advances_by_exactly_one():
    wm = _opened()
    with pytest.raises(ValueError, match="exactly one"):
        _advance(wm, 1, ROOT_1, 3, ROOT_2)


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
            wm_sig(b"\x22" * 32, WARD_ID, 1, ROOT_1, 2, ROOT_2, wm.head_nonce(WARD_ID)),
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
            wm_sig(K_SIG, WARD_ID, 1, ROOT_1, 2, ROOT_0, wm.head_nonce(WARD_ID)),
            timestamp=1000,
        )


def test_a_read_only_first_use_can_attest_without_publishing():
    """A read may be a wallet's first WARD operation, so the WM has to be able to bootstrap from
    an attestation request rather than only from a write."""
    wm = MockWM()
    fc, fr, _fhn, counter, root, _hn, _ts, _sig = wm.attest_head(
        WARD_ID, NONCE, 0, ROOT_0, head_init_sig(K_SIG, WARD_ID, 0, ROOT_0)
    )
    # AN OPENING HEAD ATTESTS ITSELF: no step produced it, so naming one would be inventing a
    # transition that never happened.
    assert (fc, fr, counter, root) == (0, ROOT_0, 0, ROOT_0)
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
    fc, fr, _fhn, tc, tr, _hn, _ts, _sig = wm3.attest_head(
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

    hn = b"\x77" * 32
    revert = wm_sig(K_SIG, WARD_ID, 1, ROOT_1, 2, ROOT_2, hn, TAG_WM_REVERT)
    ordinary = wm_sig(K_SIG, WARD_ID, 1, ROOT_1, 2, ROOT_2, hn)
    assert revert != ordinary

    # each verifies only under its own tag
    assert verify_wm_sig(WARD_ID, 1, ROOT_1, 2, ROOT_2, hn, revert, TAG_WM_REVERT)
    assert not verify_wm_sig(WARD_ID, 1, ROOT_1, 2, ROOT_2, hn, revert)
    assert verify_wm_sig(WARD_ID, 1, ROOT_1, 2, ROOT_2, hn, ordinary)
    assert not verify_wm_sig(WARD_ID, 1, ROOT_1, 2, ROOT_2, hn, ordinary, TAG_WM_REVERT)


def test_an_authorisation_moves_the_head_at_most_once():
    """THE HEAD NONCE, stated as the attack it closes.

    `(counter, root)` is not unique across a wallet's history: roots are content-addressed, so a
    tree returning to an earlier shape returns to an earlier root, and a REVERT carries an older
    root forward under a new counter on purpose. So an authorisation bound only to its endpoints
    becomes live again the moment its predecessor pair recurs, and a host that kept one can land a
    transition the user approved once at a place in history where they never approved it.

    The nonce rotates on every accepted transition, so the second attempt names a moment that has
    passed.
    """
    wm = _opened()
    stale_nonce = wm.head_nonce(WARD_ID)
    kept = wm_sig(K_SIG, WARD_ID, 1, ROOT_1, 2, ROOT_2, stale_nonce)

    # it works exactly once
    wm.advance(WARD_ID, 1, ROOT_1, 2, ROOT_2, kept, timestamp=1000)
    assert wm.head_nonce(WARD_ID) != stale_nonce

    # bring the WM back to the SAME (counter, root) predecessor a revert would create, and the
    # kept authorisation is refused -- the endpoints match, the moment does not
    _advance(wm, 2, ROOT_2, 3, ROOT_1, tag=None)
    wm.install_unauthenticated(WARD_ID, 1, ROOT_1, 1000)
    assert wm.head(WARD_ID)[:2] == (1, ROOT_1)
    with pytest.raises(ValueError, match="not authorised"):
        wm.advance(WARD_ID, 1, ROOT_1, 2, ROOT_2, kept, timestamp=1000)


# --- a superseded head nonce must never become current again -------------------------------
#
# THE ONE OBLIGATION A REAL WM CARRIES, and the property everything else about the nonce rests
# on. `(counter, root)` is not unique across a wallet's history and is not meant to be: roots are
# content-addressed, so a tree returning to an earlier shape returns to an earlier root, and a
# REVERT carries an older root forward under a new counter by design. What makes an authorisation
# single-use is therefore ONLY that the nonce moved on.
#
# The cases that make this hard are the ones where the counter and the root are SUPPOSED to go
# backwards -- a database restored from a backup, a failover onto a replica that lagged, an
# operator putting a head back by hand. All of those are legitimate for the head. None of them is
# legitimate for the nonce. The tests below cover each, and the last one shows what a WM that gets
# it wrong hands to a host that kept an old signature.


def _retired_must_stay_retired(wm, before: set, after: set) -> None:
    """Nothing that was current has been dropped, and nothing has been re-issued."""
    assert before <= after, "the ledger lost a nonce that had been current"


def test_every_head_nonce_a_wallet_ever_holds_is_distinct():
    """Across ordinary advances, a revert, and a restore that lands on an earlier head.

    Asserted over the WHOLE history rather than pairwise, because the failure this is about is
    not "the next one repeats the last" -- it is "one from six transitions ago comes back".
    """
    wm = _opened()
    seen = [wm.head_nonce(WARD_ID)]

    _advance(wm, 1, ROOT_1, 2, ROOT_2)
    seen.append(wm.head_nonce(WARD_ID))

    # back to a root this wallet already held, which is what makes the pair recur
    _advance(wm, 2, ROOT_2, 3, ROOT_1)
    seen.append(wm.head_nonce(WARD_ID))

    # a demotion: an OLDER root carried forward under a NEW counter, by construction
    from .ward_keys import TAG_WM_REVERT

    _advance(wm, 3, ROOT_1, 4, ROOT_0, tag=TAG_WM_REVERT)
    seen.append(wm.head_nonce(WARD_ID))

    # and a register restored from a backup, landing on a head held long ago
    wm.install_unauthenticated(WARD_ID, 1, ROOT_1, 1000)
    seen.append(wm.head_nonce(WARD_ID))

    assert wm.head(WARD_ID)[:2] == (1, ROOT_1)  # the HEAD really did go back...
    assert len(set(seen)) == len(seen)  # ...and the nonce really did not
    assert NO_HEAD_NONCE not in seen[1:]  # nor back to the pre-enrolment value


def test_a_restore_onto_an_earlier_head_mints_an_unused_nonce():
    """Backup restore, stated as the operation it is.

    The counter and the root are allowed to regress here -- that is the whole point of a restore.
    The nonce is not, and the check is against every value this wallet has EVER had, not merely
    against the one being replaced.
    """
    wm = _opened()
    snapshot_nonce = wm.head_nonce(WARD_ID)

    _advance(wm, 1, ROOT_1, 2, ROOT_2)
    _advance(wm, 2, ROOT_2, 3, ROOT_1)
    retired = wm.retired_nonces(WARD_ID)

    # the register comes back at the snapshot's head
    wm.install_unauthenticated(WARD_ID, 1, ROOT_1, 1000)

    assert wm.head(WARD_ID)[:2] == (1, ROOT_1)
    restored_nonce = wm.head_nonce(WARD_ID)
    assert restored_nonce != snapshot_nonce
    assert restored_nonce not in retired
    _retired_must_stay_retired(wm, retired, wm.retired_nonces(WARD_ID))


def test_a_failover_replica_may_carry_the_current_nonce_but_not_a_retired_one():
    """Handing over the CURRENT nonce is a correct failover; handing over a stale one is not.

    Worth separating because the two look alike in an operations runbook -- both are "copy the
    record to the standby" -- and only one of them is safe. What distinguishes them is not the
    head they carry but whether the nonce they carry has already been superseded.
    """
    primary = _opened()
    _advance(primary, 1, ROOT_1, 2, ROOT_2)
    current = primary.head_nonce(WARD_ID)
    counter, root, _ts = primary.head(WARD_ID)

    # A CORRECT FAILOVER: the standby takes the record as it stands, nonce included. Nothing has
    # been superseded, so an authorisation already minted against it is still good -- which is the
    # behaviour a failover must preserve, or every device in flight is stranded.
    standby = MockWM()
    standby.install_unauthenticated(WARD_ID, counter, root, 1000, head_nonce=current)
    assert standby.head_nonce(WARD_ID) == current
    in_flight = wm_sig(K_SIG, WARD_ID, 2, ROOT_2, 3, ROOT_1, current)
    standby.advance(WARD_ID, 2, ROOT_2, 3, ROOT_1, in_flight, timestamp=1000)

    # ...and once the standby has accepted it, that nonce is spent THERE too -- the failover
    # inherited the obligation along with the record. Put the head back where `in_flight` was
    # minted for, the way a second restore would, and the authorisation is refused: the endpoints
    # match, the moment does not.
    assert standby.head_nonce(WARD_ID) != current
    standby.install_unauthenticated(WARD_ID, 2, ROOT_2, 1000)
    assert standby.head(WARD_ID)[:2] == (2, ROOT_2)
    with pytest.raises(ValueError, match="not authorised"):
        standby.advance(WARD_ID, 2, ROOT_2, 3, ROOT_1, in_flight, timestamp=1000)


def test_a_kept_authorisation_is_refused_after_a_restore():
    """The operational consequence, which is what the rule is actually for.

    A host that kept a `wm_sig` waits for its `(counter, root)` predecessor to come back. A
    restore is the thing most likely to bring it back. The authorisation still names the right
    endpoints, and is refused anyway.
    """
    wm = _opened()
    kept = wm_sig(K_SIG, WARD_ID, 1, ROOT_1, 2, ROOT_2, wm.head_nonce(WARD_ID))

    wm.advance(WARD_ID, 1, ROOT_1, 2, ROOT_2, kept, timestamp=1000)
    _advance(wm, 2, ROOT_2, 3, ROOT_1)

    # the register is restored to exactly the head `kept` was minted against
    wm.install_unauthenticated(WARD_ID, 1, ROOT_1, 1000)
    assert wm.head(WARD_ID)[:2] == (1, ROOT_1)

    with pytest.raises(ValueError, match="not authorised"):
        wm.advance(WARD_ID, 1, ROOT_1, 2, ROOT_2, kept, timestamp=1000)


def test_a_wm_that_restores_a_retired_nonce_reopens_the_replay():
    """WHAT THE RULE IS WORTH, shown by breaking it.

    This is not a property of the protocol -- it is the absence of one. If a WM restores a
    superseded nonce along with the head, every authorisation ever minted against that nonce is
    live again, and the device has no way to know: it signed honestly, once, for a transition the
    user approved once. Only the WM can hold this line, which is why it is written down as an
    obligation rather than enforced by the wire.
    """
    wm = _opened()
    retired_nonce = wm.head_nonce(WARD_ID)
    kept = wm_sig(K_SIG, WARD_ID, 1, ROOT_1, 2, ROOT_2, retired_nonce)

    wm.advance(WARD_ID, 1, ROOT_1, 2, ROOT_2, kept, timestamp=1000)
    _advance(wm, 2, ROOT_2, 3, ROOT_1)
    assert retired_nonce in wm.retired_nonces(WARD_ID)

    # a restore that puts the nonce back too -- the mistake this rule names
    wm.install_unauthenticated(WARD_ID, 1, ROOT_1, 1000, head_nonce=retired_nonce)

    # and the transition lands a SECOND time, at a moment nobody authorised it for
    wm.advance(WARD_ID, 1, ROOT_1, 2, ROOT_2, kept, timestamp=1000)
    assert wm.head(WARD_ID)[:2] == (2, ROOT_2)


def test_the_mock_refuses_to_make_a_retired_nonce_current_by_accident():
    """The ledger is enforcement, not bookkeeping.

    A test that reached a repeated nonce through some future change to this mock should fail
    loudly rather than quietly assert a property it is no longer testing. Forcing one is possible
    only by naming it, which is what the test above does.
    """
    from .ward_wm import RetiredNonce

    wm = _opened()
    current = wm.head_nonce(WARD_ID)
    _advance(wm, 1, ROOT_1, 2, ROOT_2)

    # `_rotate` is the single point every current nonce comes through
    with pytest.raises(RetiredNonce):
        wm._retired[WARD_ID].add(
            wm._rotate(WARD_ID, 3, ROOT_1, wm.head_nonce(WARD_ID))
        )
        wm._rotations -= 1
        wm._rotate(WARD_ID, 3, ROOT_1, wm.head_nonce(WARD_ID))
    assert current in wm.retired_nonces(WARD_ID)


def test_an_attestation_names_the_nonce_the_step_consumed():
    """The occurrence, not just the transition.

    The attested edge is `(from, from_head_nonce) -> (to, to_head_nonce)`. A device that minted
    its authorisation under a particular nonce can read `from_head_nonce` and see that ITS
    authorisation is the one that was spent -- a question with content, because the same
    transition can occur more than once.
    """
    wm = _opened()
    consumed = wm.head_nonce(WARD_ID)

    fc, fr, from_nonce, tc, tr, to_nonce, _ts, _sig = _advance(
        wm, 1, ROOT_1, 2, ROOT_2
    )

    assert (fc, fr, tc, tr) == (1, ROOT_1, 2, ROOT_2)
    assert from_nonce == consumed  # the one the authorisation quoted
    assert to_nonce == wm.head_nonce(WARD_ID)  # the one the next must quote
    assert from_nonce != to_nonce  # every real step rotates


def test_two_occurrences_of_one_transition_are_distinguishable():
    """The same `(from, to)` pair, twice, and the attestations differ.

    Without the consumed nonce these two would be byte-identical statements -- which is precisely
    the ambiguity that let a host present an attestation of the FIRST occurrence as proof that
    the second one landed.
    """
    wm = _opened()
    first = _advance(wm, 1, ROOT_1, 2, ROOT_2)

    # bring the WM back so the very same transition can happen again
    wm.install_unauthenticated(WARD_ID, 1, ROOT_1, 1000)
    second = _advance(wm, 1, ROOT_1, 2, ROOT_2)

    # the transition is identical...
    assert first[:2] + first[3:5] == second[:2] + second[3:5]
    # ...and the occurrence is not, at either end
    assert first[2] != second[2]
    assert first[5] != second[5]
    assert first[7] != second[7]  # so the signatures differ too


def test_genesis_consumes_nothing_but_still_draws_a_live_nonce():
    """Nothing produced counter 0, so nothing was spent reaching it -- the same reason the roots
    are equal at both ends. But the head it creates is LIVE, so its nonce is a real `N0` and
    never the enrolment constant.

    `head_init_sig` is signed under NO_HEAD_NONCE because there is nothing else to quote; the
    instant it is accepted that constant stops being relevant. The firmware refuses any attested
    head carrying it, at either end.
    """
    wm = MockWM()
    fc, fr, from_nonce, tc, tr, to_nonce, _ts, _sig = wm.attest_head(
        WARD_ID, NONCE, 0, ROOT_0, head_init_sig(K_SIG, WARD_ID, 0, ROOT_0)
    )
    assert (fc, fr, tc, tr) == (0, ROOT_0, 0, ROOT_0)
    assert from_nonce == to_nonce  # nothing was consumed
    assert from_nonce == wm.head_nonce(WARD_ID)
    assert from_nonce != NO_HEAD_NONCE  # ...but it is a real one


def test_re_enrolment_after_total_loss_kills_historical_authorisations():
    """THE REASON THE ENROLMENT CONSTANT MUST NOT BE A LIVE NONCE.

    `head_init_sig` is a signature over a fixed statement and is not secret, so whoever holds one
    can re-enrol a WM that lost everything -- and nothing can stop that, because a WM with no
    register has no way to tell a genuine first contact from a replayed one.

    What CAN be stopped is that replay resurrecting old authorisations. If enrolment left the
    head at a constant, the fresh WM would sit at exactly the predecessor triple the FIRST WRITE
    was authorised against, and a retained `wm_sig` for it would land again. Genesis is not an
    obscure corner: it is where every wallet starts, and where any wallet drained back to nothing
    returns. Drawing `N0` at enrolment means the re-enrolled WM is at `N0'`, and the old
    authorisation is dead.
    """
    init = head_init_sig(K_SIG, WARD_ID, 0, ROOT_0)

    wm = MockWM()
    wm.attest_head(WARD_ID, NONCE, 0, ROOT_0, init)
    n0 = wm.head_nonce(WARD_ID)
    first_write = wm_sig(K_SIG, WARD_ID, 0, ROOT_0, 1, ROOT_1, n0)
    wm.advance(WARD_ID, 0, ROOT_0, 1, ROOT_1, first_write, timestamp=1000)

    # the WM loses everything, and the retained enrolment signature is replayed
    reborn = MockWM()
    reborn.attest_head(WARD_ID, NONCE, 0, ROOT_0, init)
    n0_prime = reborn.head_nonce(WARD_ID)

    assert reborn.head(WARD_ID)[:2] == (0, ROOT_0)  # the same head...
    assert n0_prime != n0  # ...and NOT the same moment
    assert n0_prime != NO_HEAD_NONCE

    with pytest.raises(ValueError, match="not authorised"):
        reborn.advance(WARD_ID, 0, ROOT_0, 1, ROOT_1, first_write, timestamp=1000)
