"""Unit tests for the WARD keyed path + encrypted-leaf layer (ward-design.md §1/§2/§3).

Freezes the canonical byte layout that firmware (apps/ward/service.py) and the
host (@trezor/ward) must match, and pins the "wrong/forged entry_key is
rejected" property.
"""

import os

import pytest

from trezorlib import ward_crypto as wc
from trezorlib.authdb_tree import EMPTY_ROOT, WARDTree

SEED = bytes.fromhex("11" * 64)


@pytest.fixture
def keys():
    return wc.derive_k_index(SEED), wc.derive_k_data(SEED, "address")


def test_slip21_derivation_deterministic_and_per_type():
    ki = wc.derive_k_index(SEED)
    assert len(ki) == 32 and wc.derive_k_index(SEED) == ki
    assert wc.derive_k_data(SEED, "address") != wc.derive_k_data(SEED, "label")
    assert wc.derive_k_data(SEED, "address") != ki


def test_entry_key_scope_separation_and_unforgeability(keys):
    ki, _ = keys
    ek = wc.entry_key(ki, "bitcoin", b"alice")
    variants = {
        ek,
        wc.entry_key(ki, "bitcoin", b"alice", device_id=1),
        wc.entry_key(ki, "ethereum", b"alice"),
        wc.entry_key(ki, "bitcoin", b"alice", key_type="label"),
    }
    assert len(variants) == 4, "app_id / key_type / device_id must all separate paths"
    assert wc.entry_key(b"\x11" * 32, "bitcoin", b"alice") != ek, "unforgeable w/o K_index"


def test_leaf_codec_roundtrip_and_aead_binding(keys):
    ki, kd = keys
    ek = wc.entry_key(ki, "bitcoin", b"alice")
    nonce, tag, ct = wc.encrypt_leaf(kd, ek, "address", 5, b"alice", b"data_alice")
    assert len(nonce) == 12 and len(tag) == 16 and len(ct) == 64  # bucketed
    assert wc.decrypt_leaf(kd, ek, "address", nonce, tag, ct) == (5, b"alice", b"data_alice")
    with pytest.raises(Exception):  # wrong entry_type => wrong AAD + wrong K_data
        wc.decrypt_leaf(kd, ek, "label", nonce, tag, ct)
    with pytest.raises(Exception):  # tampered ct
        wc.decrypt_leaf(kd, ek, "address", nonce, tag, ct[:-1] + bytes([ct[-1] ^ 1]))


def test_random_nonce_unique(keys):
    ki, kd = keys
    ek = wc.entry_key(ki, "bitcoin", b"x")
    n1, _, _ = wc.encrypt_leaf(kd, ek, "address", 1, b"x", b"y")
    n2, _, _ = wc.encrypt_leaf(kd, ek, "address", 1, b"x", b"y")
    assert n1 != n2


def _mk(ki, kd, ident, val, c):
    ek = wc.entry_key(ki, "bitcoin", ident)
    nonce, tag, ct = wc.encrypt_leaf(kd, ek, "address", c, ident, val)
    return ek, nonce, tag, ct


def test_tree_membership_and_nonmembership(keys):
    ki, kd = keys
    t = WARDTree()
    assert t.is_empty() and t.get_root_hash() == EMPTY_ROOT
    ekx = wc.entry_key(ki, "bitcoin", b"nobody")
    p, wk, wcm = t.get_nonmembership_proof_by_key(ekx)
    assert WARDTree.verify_nonmembership_by_key(ekx, wk, wcm, p, t.get_root_hash())

    blobs = {ident: _mk(ki, kd, ident, val, i + 1)
             for i, (ident, val) in enumerate(
                 {b"alice": b"A", b"bob": b"B", b"carol": b"C"}.items())}
    for ek, nonce, tag, ct in blobs.values():
        t.set_leaf(ek, nonce, tag, ct)
    root = t.get_root_hash()
    for ek, nonce, tag, ct in blobs.values():
        assert WARDTree.verify_proof_by_key(ek, nonce, tag, ct, t.get_proof_by_key(ek), root)

    ekabs = wc.entry_key(ki, "bitcoin", b"absent")
    p, wk, wcm = t.get_nonmembership_proof_by_key(ekabs)
    assert WARDTree.verify_nonmembership_by_key(ekabs, wk, wcm, p, root)


def test_wrong_and_forged_entry_key_rejected(keys):
    """The property the review flagged: a proof is bound to its entry_key."""
    ki, kd = keys
    t = WARDTree()
    ek_a, na, ta, ca = _mk(ki, kd, b"alice", b"A", 1)
    ek_b, nb, tb, cb = _mk(ki, kd, b"bob", b"B", 2)
    for ek, n, tg, ct in ((ek_a, na, ta, ca), (ek_b, nb, tb, cb)):
        t.set_leaf(ek, n, tg, ct)
    root = t.get_root_hash()
    proof_a = t.get_proof_by_key(ek_a)
    assert WARDTree.verify_proof_by_key(ek_a, na, ta, ca, proof_a, root)
    # a different identifier's key must not verify against alice's proof/blob
    assert not WARDTree.verify_proof_by_key(ek_b, na, ta, ca, proof_a, root)
    # a fabricated/random entry_key must not pass
    assert not WARDTree.verify_proof_by_key(os.urandom(32), na, ta, ca, proof_a, root)


def test_nonmembership_relabelled_proof_rejected():
    t = WARDTree()
    target = bytes([0x40]) + b"\x00" * 31
    witness = bytes([0x60]) + b"\x00" * 31
    other = bytes([0x80]) + b"\x00" * 31

    target_blob = (b"n" * 12, b"t" * 16, b"target", "address")
    witness_blob = (b"w" * 12, b"g" * 16, b"witness", "address")
    other_blob = (b"o" * 12, b"h" * 16, b"other", "address")
    t.set_leaf(target, target_blob[0], target_blob[1], target_blob[2], target_blob[3])
    t.set_leaf(witness, witness_blob[0], witness_blob[1], witness_blob[2], witness_blob[3])
    t.set_leaf(other, other_blob[0], other_blob[1], other_blob[2], other_blob[3])

    root = t.get_root_hash()
    proof = t.get_proof_by_key(witness)
    witness_commit = wc.commit_of(witness_blob[0], witness_blob[1], witness_blob[2])

    assert not WARDTree.verify_nonmembership_by_key(target, witness, witness_commit, proof, root)

    forged = [
        (1).to_bytes(2, "big") + (0).to_bytes(2, "big") + proof[0][4:],
        proof[1],
    ]
    assert not WARDTree.verify_nonmembership_by_key(target, witness, witness_commit, forged, root)


def test_push_flow_with_exported_keys():
    """PUSH: a host holding the exported K_index/K_data(type) computes entry_key from
    a plaintext identifier, builds the leaf+proof itself, and the device verifies it
    against its root using its own (seed-identical) K_index. Mirrors what a real
    WARDExportKeys → WARDLookup round does, without a device."""
    # device side
    dev_ki = wc.derive_k_index(SEED)
    # host receives the exported keys (same seed => identical keys)
    exp_ki = wc.derive_k_index(SEED)
    exp_kd = wc.derive_k_data(SEED, "address")
    assert exp_ki == dev_ki

    t = WARDTree()
    # host builds an entry for a known identifier using the EXPORTED keys
    host_ek = wc.entry_key(exp_ki, "bitcoin", b"carol", key_type="address")
    nonce, tag, ct = wc.encrypt_leaf(exp_kd, host_ek, "address", 7, b"carol", b"label-carol")
    t.set_leaf(host_ek, nonce, tag, ct, "address")
    root = t.get_root_hash()
    proof = t.get_proof_by_key(host_ek)

    # device recomputes entry_key from (app_id, key_type, identifier) with ITS K_index
    dev_ek = wc.entry_key(dev_ki, "bitcoin", b"carol", key_type="address")
    assert dev_ek == host_ek, "seed-identical K_index => matching path (push works)"
    assert WARDTree.verify_proof_by_key(dev_ek, nonce, tag, ct, proof, root)
    # and the device can decrypt with its own K_data
    dev_kd = wc.derive_k_data(SEED, "address")
    assert wc.decrypt_leaf(dev_kd, dev_ek, "address", nonce, tag, ct) == (7, b"carol", b"label-carol")
