"""Device tests for the WARD batch-update round and constrained one-step rollback.

Batch commit: several queued intents commit as ONE authenticated root transition
(counter += 1 for the whole batch), authenticated by head_mac + AuthCommit. Rollback
(ward-design §8.2): the host presents the FORWARD AuthCommit that created the current
head; the device verifies it to prove the predecessor and demotes to it with a
FORWARD-incrementing counter (so the counter stays monotone — the anti-replay epoch).

The WARD Manager's final attestation is signed locally with the debug WM key
(ward_mgr_emu), accepted only on debug firmware.

Multi-leaf batches support shape-preserving updates over the pre-batch root.
Inserts and deletes must use single-leaf commits.
"""

import pytest

from trezorlib import messages, ward
from trezorlib.authdb_tree import WARDTree
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import Cancelled, TrezorFailure
from trezorlib.testing.device_handler import BackgroundDeviceHandler

from ...ward_mgr_emu import sign_ward_update
from .test_ward import (
    _APP,
    _apply_device_leaf,
    _queue_update,
    _seed_device,
    _tree,
)

pytestmark = pytest.mark.models("core")

ENTRIES = {b"alice": b"data_alice", b"bob": b"data_bob"}


def _seeded():
    """Host tree with two entries + the device seeded to its root; returns
    (tree, counter)."""
    tree = _tree()
    for addr, val in ENTRIES.items():
        tree.insert(_APP, addr, val, counter=1)
    return tree


def _register_callback(session: Session, tree: WARDTree) -> None:
    session.client.app.ward_proof_callback = ward.tree_proof_callback(tree)


def _commit_batch(session: Session, tree: WARDTree, pending_ids: list) -> tuple:
    """perform_batch -> WM-sign the head -> confirmed_batch_by_wm. Applies every
    returned device leaf to `tree` so it tracks the device root. Returns
    (counter, new_root, from_root, auth_commit)."""
    _register_callback(session, tree)
    (
        counter,
        from_root,
        new_root,
        mac,
        ward_id,
        _head_mac,
        auth_commit,
        _sig,
        leaves,
    ) = ward.perform_batch(session, pending_ids)
    assert ward_id is not None
    mac_for_sig = mac if mac is not None else ward.ZERO_MAC
    sig = sign_ward_update(counter, mac_for_sig, ward_id)
    out_counter, out_root, _wid, _root_mac = ward.confirmed_batch_by_wm(
        session, counter, mac, sig
    )
    for lf in leaves:  # (entry_key, LeafBlob)
        _apply_device_leaf(tree, (None,) * 4 + lf)
    return out_counter, out_root, from_root, auth_commit


def _perform_revert(session: Session, *args, approve: bool = True) -> tuple:
    """WARDPerformRevert through its trusted "Undo WARD change" screen."""
    with session.test_ctx as client:
        with BackgroundDeviceHandler(client) as dev:
            dev.run_with_provided_session(
                session, lambda s: ward.perform_revert(s, *args)
            )
            if approve:
                dev.debuglink().press_yes()
            else:
                dev.debuglink().press_no()
            return dev.result()


def _bit(entry_key: bytes, bit: int) -> int:
    return (entry_key[bit // 8] >> (7 - bit % 8)) & 1


def test_ward_batch_single_commit(session: Session) -> None:
    """A batch of one intent commits as a single transition (counter += 1) and the
    installed root matches the host tree."""
    tree = _seeded()
    counter0 = _seed_device(session, tree)

    pid = _queue_update(session, b"carol", b"", b"data_carol")
    counter, new_root, _from_root, _ac = _commit_batch(session, tree, [pid])

    assert counter == counter0 + 1
    assert new_root == tree.get_root_hash()


def test_ward_batch_multi_commit(session: Session) -> None:
    """N>1 UPDATES of existing leaves commit as ONE transition advancing the counter
    by exactly 1 (not by N), via the shape-preserving multiproof over the pre-batch
    root."""
    tree = _seeded()
    counter0 = _seed_device(session, tree)

    # Both leaves already exist (seeded), so this is a shape-preserving update batch.
    p1 = _queue_update(session, b"alice", ENTRIES[b"alice"], b"data_alice_v2")
    p2 = _queue_update(session, b"bob", ENTRIES[b"bob"], b"data_bob_v2")
    counter, new_root, _from_root, _ac = _commit_batch(session, tree, [p1, p2])

    assert counter == counter0 + 1  # whole batch is ONE transition
    assert new_root == tree.get_root_hash()


def test_ward_batch_multi_insert_rejected(session: Session) -> None:
    """A multi-leaf batch containing an INSERT (shape change) is rejected — inserts /
    deletes must use single-leaf commits until the general shape-changing multiproof
    lands. (Documents the current constraint of compute_batch_root.)"""
    tree = _seeded()
    _seed_device(session, tree)

    p1 = _queue_update(session, b"alice", ENTRIES[b"alice"], b"data_alice_v2")  # update
    p2 = _queue_update(session, b"carol", b"", b"data_carol")  # insert -> shape change
    _register_callback(session, tree)
    with pytest.raises(TrezorFailure):
        ward.perform_batch(session, [p1, p2])


def test_ward_batch_rejects_an_update_hidden_behind_another_leaf(
    session: Session,
) -> None:
    """A host pairs a genuine update of alice with an "update" of an ABSENT entry,
    serving a stale sealed leaf it kept from history and a forged proof that walks
    through alice's leaf. The multiproof used to read alice's leaf at that position,
    ignore the forged item, match the stored root, and commit only alice's change --
    an approved write that silently never happened. It must be refused."""
    tree = _seeded()
    _seed_device(session, tree)

    def ek(addr: bytes) -> bytes:
        return tree._ek(_APP, addr, "address", 0)

    alice, bob = ek(b"alice"), ek(b"bob")
    split = next(b for b in range(256) if _bit(alice, b) != _bit(bob, b))
    # an absent entry on alice's side of the only branch: its path ends at her leaf
    victim = next(
        v
        for v in (b"victim%d" % i for i in range(64))
        if _bit(ek(v), split) == _bit(alice, split)
    )
    history = _tree()
    history.insert(_APP, victim, b"victim_old", counter=1)
    stale = history.leaf_blob(_APP, victim)
    assert stale is not None

    p1 = _queue_update(session, b"alice", ENTRIES[b"alice"], b"data_alice_v2")
    p2 = _queue_update(session, victim, b"victim_old", b"victim_new")

    honest = ward.tree_proof_callback(tree)

    def forged(msg: messages.WARDProofRequest) -> messages.WARDProofAck:
        if msg.entry_key != ek(victim):
            return honest(msg)
        return messages.WARDProofAck(
            proof=[(split + 1).to_bytes(2, "big") + b"\x55" * 32]
            + tree.get_proof_by_key(alice),
            content=ward.make_leaf_content(stale.content),
            identity=ward.make_leaf_identity(stale.key_type, stale.identity),
        )

    session.client.app.ward_proof_callback = forged
    with pytest.raises(TrezorFailure, match="another leaf"):
        ward.perform_batch(session, [p1, p2])


def test_ward_rollback_one_step(session: Session) -> None:
    """Two single-leaf batch commits, then a constrained one-step rollback of the
    second: the head returns to the predecessor root with a forward-incremented
    counter, proven by the second batch's own forward AuthCommit."""
    tree = _seeded()
    c0 = _seed_device(session, tree)

    # Commit #1: insert carol  -> R1 at c0+1
    p1 = _queue_update(session, b"carol", b"", b"data_carol")
    c1, r1, _f1, _ac1 = _commit_batch(session, tree, [p1])
    assert c1 == c0 + 1

    # Snapshot the tree at R1 so we can restore it after the rollback.
    tree_at_r1 = _tree()
    for addr in (b"alice", b"bob", b"carol"):
        leaf = tree.get_leaf(tree._ek(_APP, addr, "address", 0))
        assert leaf is not None
        tree_at_r1.set_leaf(tree._ek(_APP, addr, "address", 0), leaf)
    assert tree_at_r1.get_root_hash() == r1

    # Commit #2: insert dave  -> R2 at c0+2 ; capture its forward AuthCommit + from_root(=R1)
    p2 = _queue_update(session, b"dave", b"", b"data_dave")
    c2, r2, from_root2, ac2 = _commit_batch(session, tree, [p2])
    assert c2 == c0 + 2 and from_root2 == r1

    # Roll back commit #2. The predecessor (R1) is proven by ac2, not host-named.
    (
        to_counter,
        from_root,
        new_root,
        mac,
        ward_id,
        _hm,
        _ar,
        _sig,
    ) = _perform_revert(session, c2, r2, from_root2, ac2)
    assert to_counter == c2 + 1  # forward-increment
    assert from_root == r2
    mac_for_sig = mac if mac is not None else ward.ZERO_MAC
    sig = sign_ward_update(to_counter, mac_for_sig, ward_id)
    out_counter, out_root, _w, _rm = ward.confirmed_revert_by_wm(
        session, to_counter, mac, sig
    )

    assert out_counter == c0 + 3
    assert out_root == r1  # head demoted to the predecessor
    assert out_root == tree_at_r1.get_root_hash()


def test_ward_rollback_rejects_wrong_predecessor(session: Session) -> None:
    """A rollback whose forward AuthCommit does not authenticate the claimed
    predecessor is rejected — the host cannot name an arbitrary rewind target. It
    fails before the confirmation screen, so no input is needed here."""
    tree = _seeded()
    c0 = _seed_device(session, tree)
    p1 = _queue_update(session, b"carol", b"", b"data_carol")
    c1, r1, from_root1, ac1 = _commit_batch(session, tree, [p1])

    bogus_prev = b"\x99" * 32  # not the real predecessor encoded in ac1
    with pytest.raises(TrezorFailure):
        ward.perform_revert(session, c1, r1, bogus_prev, ac1)


def test_ward_rollback_requires_user_confirmation(session: Session) -> None:
    """Undoing a change is the user's decision: the device asks before K_sig signs the
    revert (the signature the WM accepts). Declining leaves nothing to install."""
    tree = _seeded()
    _seed_device(session, tree)
    p1 = _queue_update(session, b"carol", b"", b"data_carol")
    c1, r1, from_root1, ac1 = _commit_batch(session, tree, [p1])

    with pytest.raises(Cancelled):
        _perform_revert(session, c1, r1, from_root1, ac1, approve=False)

    with pytest.raises(TrezorFailure, match="no committed rollback"):
        ward.confirmed_revert_by_wm(session, c1 + 1, None, b"\x01" * 64)
