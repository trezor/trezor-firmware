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
from .ward_wm import MockWM

K_SIG = b"\x11" * 32
WARD_ID = _ed25519.publickey_unsafe(K_SIG)
ROOT_0 = b"\x00" * 31 + b"\x01"
ROOT_1 = b"\xaa" * 32
ROOT_2 = b"\xbb" * 32
NONCE = b"\x99" * 32


def _advance(wm, frm, from_root, to, to_root, tag=None, **kw):
    sig = (
        wm_sig(K_SIG, WARD_ID, frm, from_root, to, to_root)
        if tag is None
        else wm_sig(K_SIG, WARD_ID, frm, from_root, to, to_root, tag)
    )
    return wm.publish_and_attest(
        WARD_ID, NONCE, frm, from_root, to, to_root, sig, timestamp=1000, **kw
    )


def _opened() -> MockWM:
    wm = MockWM()
    _advance(wm, 0, ROOT_0, 1, ROOT_1, head_init_sig=head_init_sig(K_SIG, WARD_ID, 0, ROOT_0))
    return wm


def test_an_unknown_wallet_needs_head_init():
    """Otherwise whoever speaks first chooses a wallet's opening head."""
    wm = MockWM()
    with pytest.raises(ValueError, match="head-init"):
        _advance(wm, 0, ROOT_0, 1, ROOT_1)


def test_head_init_must_be_authorised():
    wm = MockWM()
    other = head_init_sig(b"\x22" * 32, WARD_ID, 0, ROOT_0)
    with pytest.raises(ValueError, match="head-init"):
        _advance(wm, 0, ROOT_0, 1, ROOT_1, head_init_sig=other)


def test_head_init_names_the_head_it_opens():
    """A signature over one opening head must not open a different one."""
    wm = MockWM()
    with pytest.raises(ValueError, match="head-init"):
        _advance(
            wm, 0, ROOT_2, 1, ROOT_1, head_init_sig=head_init_sig(K_SIG, WARD_ID, 0, ROOT_0)
        )


def test_a_first_head_starts_at_zero():
    """SIGNED FOR COUNTER 7, so the rule under test is the one that actually fires.

    The init signature names the counter it opens as well as the root, so offering a signature
    minted for counter 0 here would be refused as unauthorised and never reach this rule -- which
    is a strengthening rather than an obstacle, and worth having a test walk past deliberately.
    """
    wm = MockWM()
    with pytest.raises(ValueError, match="counter 0"):
        _advance(
            wm,
            7,
            ROOT_0,
            8,
            ROOT_1,
            head_init_sig=head_init_sig(K_SIG, WARD_ID, 7, ROOT_0),
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
        + bytes([4])
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
            wm_sig(b"\x22" * 32, WARD_ID, 1, ROOT_1, 2, ROOT_2),
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
            wm_sig(K_SIG, WARD_ID, 1, ROOT_1, 2, ROOT_0),
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
    # and the head it adopted is now the one an advance must build on
    _advance(wm, 0, ROOT_0, 1, ROOT_1)
    assert wm.head(WARD_ID)[:2] == (1, ROOT_1)


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
