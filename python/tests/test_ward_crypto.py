"""Unit tests for the WARD keyed path + two-part leaf layer (ward-design.md §1/§2/§3,
ToDo-leaf_structure.md).

Freezes the canonical byte layout that firmware (apps/ward/service.py) and the host
(@trezor/ward) must match, pins the "wrong/forged MAC is rejected" property, and
asserts the disclosure tiers the two-key split exists for.
"""

import os

import pytest

from trezorlib import ward_crypto as wc
from trezorlib.authdb_tree import EMPTY_ROOT, WARDTree

SEED = bytes.fromhex("11" * 64)


@pytest.fixture
def keys():
    """(K_path, K_ident(address), K_data(address))."""
    return (
        wc.derive_k_path(SEED),
        wc.derive_k_ident(SEED, "address"),
        wc.derive_k_data(SEED, "address"),
    )


def _leaf(ki, kd, mac, ident, val, c, app_id="bitcoin", **kw):
    return wc.encode_leaf(ki, kd, mac, "address", c, ident, app_id, val, **kw)


# --- key derivation ---


def test_slip21_derivation_deterministic_and_per_type():
    kp = wc.derive_k_path(SEED)
    assert len(kp) == 32 and wc.derive_k_path(SEED) == kp
    for derive in (wc.derive_k_ident, wc.derive_k_data):
        assert derive(SEED, "address") != derive(SEED, "label"), "per-key_type"
        assert derive(SEED, "address") != kp
    # K_ident and K_data must be independent: neither can open the other's part
    assert wc.derive_k_ident(SEED, "address") != wc.derive_k_data(SEED, "address")


def test_mac_scope_separation_and_unforgeability(keys):
    kp, _, _ = keys
    mac = wc.leaf_identity_mac(kp, "bitcoin", b"alice")
    variants = {
        mac,
        wc.leaf_identity_mac(kp, "bitcoin", b"alice", device_id=1),
        wc.leaf_identity_mac(kp, "ethereum", b"alice"),
        wc.leaf_identity_mac(kp, "bitcoin", b"alice", key_type="label"),
    }
    assert len(variants) == 4, "app_id / key_type / device_id must all separate paths"
    assert wc.leaf_identity_mac(b"\x11" * 32, "bitcoin", b"alice") != mac, "needs K_path"
    assert wc.entry_key is wc.leaf_identity_mac, "wire name is an alias"


# --- the two parts ---


def test_identity_part_roundtrip_and_padding(keys):
    kp, ki, _ = keys
    mac = wc.leaf_identity_mac(kp, "bitcoin", b"alice", device_id=3)
    part = wc.encode_identity(ki, mac, "address", b"alice", "bitcoin", 3)
    assert part.encoding == wc.ENC_ENCRYPTED
    assert len(part.nonce) == 12 and len(part.tag) == 16
    assert len(part.body) == 64, "bucket-padded, so identifier length does not leak"
    assert wc.decode_identity(ki, mac, "address", part) == (b"alice", b"bitcoin", 3)
    # a 200-byte identifier lands in the next bucket, not a distinct length
    long_part = wc.encode_identity(ki, mac, "address", b"x" * 200, "bitcoin", 3)
    assert len(long_part.body) == 256


def test_content_part_roundtrip(keys):
    kp, _, kd = keys
    mac = wc.leaf_identity_mac(kp, "bitcoin", b"alice")
    part = wc.encode_content(kd, mac, "address", 5, b"data_alice")
    assert len(part.body) == 64
    assert wc.decode_content(kd, mac, "address", part) == (5, b"data_alice")
    assert b"data_alice" not in part.body


def test_parts_are_independently_keyed(keys):
    """The point of the split: K_ident reads identities and nothing else; K_data reads
    values and nothing else."""
    kp, ki, kd = keys
    mac = wc.leaf_identity_mac(kp, "bitcoin", b"alice")
    leaf = _leaf(ki, kd, mac, b"alice", b"secret", 1)

    # K_ident holder: identity yes, value no
    assert wc.decode_identity(ki, mac, "address", leaf.identity)[0] == b"alice"
    with pytest.raises(Exception):
        wc.decode_content(ki, mac, "address", leaf.content)
    # K_data holder: value yes, identity no
    assert wc.decode_content(kd, mac, "address", leaf.content) == (1, b"secret")
    with pytest.raises(Exception):
        wc.decode_identity(kd, mac, "address", leaf.identity)


def test_aad_binds_part_to_mac_type_and_domain(keys):
    kp, ki, kd = keys
    mac = wc.leaf_identity_mac(kp, "bitcoin", b"alice")
    other = wc.leaf_identity_mac(kp, "bitcoin", b"bob")
    ident = wc.encode_identity(ki, mac, "address", b"alice", "bitcoin", 0)

    with pytest.raises(Exception):  # moved to another MAC
        wc.decode_identity(ki, other, "address", ident)
    with pytest.raises(Exception):  # moved to another key_type
        wc.decode_identity(ki, mac, "label", ident)
    with pytest.raises(Exception):  # tampered ciphertext
        bad = ident._replace(body=ident.body[:-1] + bytes([ident.body[-1] ^ 1]))
        wc.decode_identity(ki, mac, "address", bad)
    # domain separation: an identity part must not open as a content part even under
    # the right key, because the AAD domain byte differs (0x03 vs 0x02)
    ident_under_kd = wc.encode_identity(kd, mac, "address", b"alice", "bitcoin", 0)
    with pytest.raises(Exception):
        wc.decode_content(kd, mac, "address", ident_under_kd)


def test_random_nonce_unique_per_part(keys):
    kp, ki, kd = keys
    mac = wc.leaf_identity_mac(kp, "bitcoin", b"x")
    n1 = wc.encode_identity(ki, mac, "address", b"x", "bitcoin", 0).nonce
    n2 = wc.encode_identity(ki, mac, "address", b"x", "bitcoin", 0).nonce
    n3 = wc.encode_content(kd, mac, "address", 1, b"y").nonce
    assert len({n1, n2, n3}) == 3, "fresh nonce per part per write (§4.5)"


# --- commit ---


def test_commit_covers_both_parts_and_key_type(keys):
    kp, ki, kd = keys
    mac = wc.leaf_identity_mac(kp, "bitcoin", b"alice")
    leaf = _leaf(ki, kd, mac, b"alice", b"A", 1)
    base = wc.commit_of(leaf)

    assert wc.commit_of(leaf._replace(key_type="label")) != base
    assert wc.commit_of(leaf._replace(identity=wc.EMPTY_PART)) != base
    assert wc.commit_of(leaf._replace(content=wc.EMPTY_PART)) != base
    # any byte of either part changes the commit -> integrity comes from the root
    tampered = leaf.content._replace(body=leaf.content.body[:-1] + b"\xff")
    assert wc.commit_of(leaf._replace(content=tampered)) != base


def test_all_four_encoding_combinations_commit_distinctly(keys):
    kp, ki, kd = keys
    mac = wc.leaf_identity_mac(kp, "bitcoin", b"alice")
    commits = {
        wc.commit_of(
            _leaf(ki, kd, mac, b"alice", b"A", 1, plaintext_identity=pi, plaintext_content=pc)
        )
        for pi in (False, True)
        for pc in (False, True)
    }
    assert len(commits) == 4, "the encoding byte is inside the commit"


def test_plaintext_parts_are_keyless_readable(keys):
    """§3.10: sealing is a per-part deployment choice. A plaintext part is readable
    with no key at all, and still committed identically by a keyless host."""
    kp, ki, kd = keys
    mac = wc.leaf_identity_mac(kp, "bitcoin", b"alice")
    leaf = _leaf(ki, kd, mac, b"alice", b"A", 9, plaintext_identity=True, plaintext_content=True)
    assert leaf.identity.encoding == wc.ENC_PLAINTEXT
    assert wc.unpack_identity(leaf.identity.body) == (b"alice", b"bitcoin", 0)
    assert wc.unpack_content(leaf.content.body) == (9, b"A")
    # and the keyless commit is reproducible from the stored bytes alone
    assert wc.commit_of(leaf) == wc.commit_of(
        wc.LeafBlob(leaf.key_type, leaf.identity, leaf.content)
    )


def test_delete_is_a_full_delete(keys):
    """A delete REMOVES the leaf; it is not an update to an empty value. So both parts
    are empty (nothing left to describe — no tombstone), the leaf is gone from the
    trie, and its absence is provable."""
    kp, ki, kd = keys
    mac = wc.leaf_identity_mac(kp, "bitcoin", b"gone")
    leaf = _leaf(ki, kd, mac, b"gone", b"", 3)

    assert leaf.is_delete()
    assert leaf.content.is_empty(), "content part empty"
    assert leaf.identity.is_empty(), "identity part empty too — no tombstone remains"

    t = WARDTree(kp, kd, ki)
    other = wc.leaf_identity_mac(kp, "bitcoin", b"stays")
    t.set_leaf(mac, _leaf(ki, kd, mac, b"gone", b"v", 1))
    t.set_leaf(other, _leaf(ki, kd, other, b"stays", b"w", 1))
    assert t.get_leaf(mac) is not None

    t.set_leaf(mac, leaf)
    # gone, not present-with-empty-value
    assert t.get_leaf(mac) is None
    assert t.get_value("bitcoin", b"gone") == b""
    assert t.get_counter("bitcoin", b"gone") == 0

    # and the path is provably absent against the resulting root
    root = t.get_root_hash()
    proof, w_key, w_commit = t.get_nonmembership_proof_by_key(mac)
    assert WARDTree.verify_nonmembership_by_key(mac, w_key, w_commit, proof, root)

    # deleting the last leaf empties the tree entirely
    t.set_leaf(other, _leaf(ki, kd, other, b"stays", b"", 2))
    assert t.is_empty()


# --- trie ---


def test_tree_membership_and_nonmembership(keys):
    kp, ki, kd = keys
    t = WARDTree(kp, kd, ki)
    assert t.is_empty() and t.get_root_hash() == EMPTY_ROOT
    macx = wc.leaf_identity_mac(kp, "bitcoin", b"nobody")
    p, wk, wcm = t.get_nonmembership_proof_by_key(macx)
    assert WARDTree.verify_nonmembership_by_key(macx, wk, wcm, p, t.get_root_hash())

    leaves = {}
    for i, (ident, val) in enumerate({b"alice": b"A", b"bob": b"B", b"carol": b"C"}.items()):
        mac = wc.leaf_identity_mac(kp, "bitcoin", ident)
        leaves[mac] = _leaf(ki, kd, mac, ident, val, i + 1)
        t.set_leaf(mac, leaves[mac])
    root = t.get_root_hash()
    for mac, leaf in leaves.items():
        assert WARDTree.verify_proof_by_key(mac, leaf, t.get_proof_by_key(mac), root)

    mac_abs = wc.leaf_identity_mac(kp, "bitcoin", b"absent")
    p, wk, wcm = t.get_nonmembership_proof_by_key(mac_abs)
    assert WARDTree.verify_nonmembership_by_key(mac_abs, wk, wcm, p, root)


def test_wrong_and_forged_mac_rejected(keys):
    """A proof is bound to its MAC."""
    kp, ki, kd = keys
    t = WARDTree(kp, kd, ki)
    mac_a = wc.leaf_identity_mac(kp, "bitcoin", b"alice")
    mac_b = wc.leaf_identity_mac(kp, "bitcoin", b"bob")
    leaf_a = _leaf(ki, kd, mac_a, b"alice", b"A", 1)
    t.set_leaf(mac_a, leaf_a)
    t.set_leaf(mac_b, _leaf(ki, kd, mac_b, b"bob", b"B", 2))
    root = t.get_root_hash()
    proof_a = t.get_proof_by_key(mac_a)

    assert WARDTree.verify_proof_by_key(mac_a, leaf_a, proof_a, root)
    assert not WARDTree.verify_proof_by_key(mac_b, leaf_a, proof_a, root)
    assert not WARDTree.verify_proof_by_key(os.urandom(32), leaf_a, proof_a, root)


def test_any_part_mutation_fails_root_verification(keys):
    """§3.3: integrity comes from the root, not the AEAD — so section-splicing by a
    host is caught even though each part is authenticated separately."""
    kp, ki, kd = keys
    t = WARDTree(kp, kd, ki)
    mac = wc.leaf_identity_mac(kp, "bitcoin", b"alice")
    leaf = _leaf(ki, kd, mac, b"alice", b"A", 1)
    t.set_leaf(mac, leaf)
    mac_b = wc.leaf_identity_mac(kp, "bitcoin", b"bob")
    t.set_leaf(mac_b, _leaf(ki, kd, mac_b, b"bob", b"B", 1))
    root = t.get_root_hash()
    proof = t.get_proof_by_key(mac)

    for mutated in (
        leaf._replace(identity=wc.EMPTY_PART),  # identity stripped
        leaf._replace(content=wc.EMPTY_PART),  # content stripped
        leaf._replace(key_type="label"),  # clear field swapped
        leaf._replace(identity=leaf.identity._replace(encoding=wc.ENC_PLAINTEXT)),
    ):
        assert not WARDTree.verify_proof_by_key(mac, mutated, proof, root)


def test_nonmembership_relabelled_proof_rejected(keys):
    kp, ki, kd = keys
    t = WARDTree(kp, kd, ki)
    target = bytes([0x40]) + b"\x00" * 31
    witness = bytes([0x60]) + b"\x00" * 31
    other = bytes([0x80]) + b"\x00" * 31

    blobs = {
        target: _leaf(ki, kd, target, b"t", b"target", 1),
        witness: _leaf(ki, kd, witness, b"w", b"witness", 1),
        other: _leaf(ki, kd, other, b"o", b"other", 1),
    }
    for mac, leaf in blobs.items():
        t.set_leaf(mac, leaf)

    root = t.get_root_hash()
    proof = t.get_proof_by_key(witness)
    witness_commit = wc.commit_of(blobs[witness])

    assert not WARDTree.verify_nonmembership_by_key(target, witness, witness_commit, proof, root)

    forged = [
        (1).to_bytes(2, "big") + (0).to_bytes(2, "big") + proof[0][4:],
        proof[1],
    ]
    assert not WARDTree.verify_nonmembership_by_key(target, witness, witness_commit, forged, root)


# --- what the change is for ---


def test_leaf_is_self_describing(keys):
    """The gap this format closes: recover the whole MAC preimage from the leaf, and
    verify the stored MAC really is the MAC of that identity."""
    kp, ki, kd = keys
    mac = wc.leaf_identity_mac(kp, "ethereum", b"0xabc", key_type="label", device_id=7)
    leaf = wc.encode_leaf(ki, kd, mac, "label", 4, b"0xabc", "ethereum", b"v", 7)

    c_leaf, identifier, app_id, device_id, value = wc.decode_leaf(ki, kd, mac, leaf)
    assert (identifier, app_id, device_id, leaf.key_type) == (b"0xabc", b"ethereum", 7, "label")
    assert (c_leaf, value) == (4, b"v")
    assert wc.verify_mac(kp, mac, leaf, ki)

    # a record whose MAC was swapped for another leaf's is detected
    wrong_mac = wc.leaf_identity_mac(kp, "ethereum", b"0xdef", key_type="label", device_id=7)
    with pytest.raises(Exception):  # AAD binds the identity to its MAC
        wc.verify_mac(kp, wrong_mac, leaf, ki)


def test_locating_a_leaf_needs_no_key(keys):
    """The MAC is stored, so proof serving is keyless in either mode — a host with no
    keys at all serves a membership proof for a fully sealed leaf."""
    kp, ki, kd = keys
    mac = wc.leaf_identity_mac(kp, "bitcoin", b"alice")
    leaf = _leaf(ki, kd, mac, b"alice", b"A", 1)

    keyless = WARDTree()  # no device keys supplied
    keyless.set_leaf(mac, leaf)
    root = keyless.get_root_hash()
    assert WARDTree.verify_proof_by_key(mac, leaf, keyless.get_proof_by_key(mac), root)


def test_push_identifier_to_mac_index():
    """PUSH resolves identifier -> MAC. Plaintext identity needs no keys; encrypted
    identity needs K_ident and nothing more. Neither needs K_data."""
    kp = wc.derive_k_path(SEED)
    ki = wc.derive_k_ident(SEED, "address")
    kd = wc.derive_k_data(SEED, "address")

    macs = {}
    rows = []  # what the host stores: (mac, leaf)
    for ident in (b"carol", b"dave"):
        mac = wc.leaf_identity_mac(kp, "bitcoin", ident)
        macs[ident] = mac
        rows.append((mac, _leaf(ki, kd, mac, ident, b"label-" + ident, 7)))

    # encrypted identity: K_ident alone builds the index, and cannot read values
    index = {}
    for mac, leaf in rows:
        identifier, app_id, _dev = wc.decode_identity(ki, mac, leaf.key_type, leaf.identity)
        index[(app_id, identifier)] = mac
        with pytest.raises(Exception):
            wc.decode_content(ki, mac, leaf.key_type, leaf.content)
    assert index[(b"bitcoin", b"carol")] == macs[b"carol"]

    # plaintext identity: the same index with no keys at all
    plain_rows = [
        (mac, _leaf(ki, kd, mac, ident, b"v", 1, plaintext_identity=True))
        for ident, mac in macs.items()
    ]
    keyless_index = {
        wc.unpack_identity(leaf.identity.body)[:2][::-1]: mac for mac, leaf in plain_rows
    }
    assert keyless_index[(b"bitcoin", b"carol")] == macs[b"carol"]


# --- frozen vectors ---


def test_frozen_vectors():
    """Pins the canonical bytes so a change to any of the three implementations
    (firmware apps/ward/service.py, this module, @trezor/ward) is caught here rather
    than at the emulator. Verified byte-identical against service.py in CPython."""
    kp = wc.derive_k_path(SEED)
    ki = wc.derive_k_ident(SEED, "address")
    kd = wc.derive_k_data(SEED, "address")
    assert kp.hex() == "61d6a580121fc98b7bad5ffa0b96552306222c4d97a410dc80e86b837db263c6"
    assert ki.hex() == "5d9542d7e3ca96a17077ea4889ad6461ae63a78cd3e0779a4135d6feeb0ea3b4"
    assert kd.hex() == "9ae3bc6866b853cffc237fa11437e68d41ed91c9b8811e2b50a3f4f1cd0aa3e5"

    mac = wc.leaf_identity_mac(kp, "bitcoin", b"alice", "address", 7)
    assert mac.hex() == "20f3088c1a70e4749e21b2f1969b6f982ced4f8d1983cdda856b292bbb51750a"

    nonce = b"\x5a" * 12
    leaf = wc.LeafBlob(
        "address",
        wc.encode_identity(ki, mac, "address", b"alice", "bitcoin", 7, nonce=nonce),
        wc.encode_content(kd, mac, "address", 5, b"data_alice", nonce=nonce),
    )
    commit = wc.commit_of(leaf)
    assert commit.hex() == "4e2f5c55548a63a56e10eed9b00b4eaebe7b27ece484aefe319ffdd5b8c3e534"
    assert (
        wc.leaf_hash_of(mac, commit).hex()
        == "ff2d92fe3997f4c2201aa3060c3b2f2fa8bf7e72f463caa63489c95122c57400"
    )
