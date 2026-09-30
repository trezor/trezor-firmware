# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
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

"""trezorlib's WARD trie: pinned to the firmware's vectors, and to its own rebuild.

The vectors are the ones `core/tests/test_apps.ward.py` `TestWardTrie` pins, so this and the
firmware verifier are held to the same bytes. The property tests drive the verifier's
insert / delete / update against the store's canonical rebuild: a derived root that drifts from
the rebuild is exactly the bug a single proof cannot show.
"""

import random
from types import SimpleNamespace

import pytest

from trezorlib.ward_trie import (
    EMPTY_ROOT,
    OP_COMMIT,
    OP_REVERT,
    Link,
    TransitionLog,
    WardTrie,
    WardTrieError,
    addr_bit,
    check_shape,
    commit_of,
    delete_root,
    fold,
    insert_root,
    internal_hash,
    leaf_hash,
    proof_elem,
    update_root,
    verify_membership,
    verify_nonmembership,
)

# --- the firmware's frozen four-leaf vectors --------------------------------------------------

ROOT = bytes.fromhex("2b4e46b341ecf5ebbb506bb6878e1523dff181e103ede3c683c955d34302fa1e")
MEMBER = bytes.fromhex("358b7591f24d313e523c7b34b8bd513e4310e08d058aee11d679ba41958853fe")
ABSENT = bytes.fromhex("5ad38304b535c2987dbd24657c1a11b884984ff600d9f389deb0d4e634fee792")
WITNESS_COMMIT = bytes.fromhex(
    "2a36629301c9f5965be929bdbb741bbf5980f3829349748045ce20130496bb54"
)
PROOF = [
    bytes.fromhex("0000e96a5c3627be9ad15ae404da1ac72b42f1a602039dbc46fa22eb52e6071949d3")
]


def test_empty_root_is_sha256_of_0x03() -> None:
    assert EMPTY_ROOT.hex() == (
        "084fed08b978af4d7d196a7446a86b58009e636b611db16211b65a9aadff29c5"
    )


def test_frozen_membership_and_absence() -> None:
    assert verify_membership(MEMBER, WITNESS_COMMIT, PROOF, ROOT)
    assert verify_nonmembership(ABSENT, MEMBER, WITNESS_COMMIT, PROOF, ROOT)
    # the witness equal to the target proves presence, not absence
    assert not verify_nonmembership(MEMBER, MEMBER, WITNESS_COMMIT, PROOF, ROOT)


def test_bit_order_is_msb_first() -> None:
    key = bytes.fromhex("80" + "00" * 31)
    assert [addr_bit(key, i) for i in range(3)] == [1, 0, 0]
    assert addr_bit(bytes.fromhex("00" + "80" + "00" * 30), 8) == 1


def test_a_relabelled_split_bit_is_refused() -> None:
    relabelled = [bytes([0, 1]) + PROOF[0][2:]]
    assert not verify_nonmembership(ABSENT, MEMBER, WITNESS_COMMIT, relabelled, ROOT)


@pytest.mark.parametrize(
    "proof",
    [
        [bytes([1, 0]) + bytes(32)],  # split_bit 256
        [bytes(33)],  # short element
        [bytes(35)],  # long element
        [proof_elem(1, bytes(32)), proof_elem(4, bytes(32))],  # reversed
        [proof_elem(1, bytes(32)), proof_elem(1, bytes(32))],  # repeated
    ],
)
def test_malformed_proofs_are_refused_before_hashing(proof: list) -> None:
    with pytest.raises(WardTrieError):
        check_shape(proof)


def test_widths_are_enforced() -> None:
    with pytest.raises(WardTrieError):
        leaf_hash(MEMBER + WITNESS_COMMIT[:1], WITNESS_COMMIT[1:])  # the boundary shift
    with pytest.raises(WardTrieError):
        fold(bytes(32), [], bytes(31))
    with pytest.raises(WardTrieError):
        verify_nonmembership(ABSENT, MEMBER + b"\x00", WITNESS_COMMIT, PROOF, ROOT)


def test_an_unsettled_root_is_refused() -> None:
    with pytest.raises(WardTrieError):
        insert_root(MEMBER, WITNESS_COMMIT, [], None)
    with pytest.raises(WardTrieError):
        delete_root(MEMBER, WITNESS_COMMIT, PROOF, None)


def test_a_non_empty_tree_needs_a_witness() -> None:
    with pytest.raises(WardTrieError):
        insert_root(ABSENT, WITNESS_COMMIT, [], ROOT)
    with pytest.raises(WardTrieError):
        insert_root(ABSENT, WITNESS_COMMIT, PROOF, EMPTY_ROOT, MEMBER, WITNESS_COMMIT)


# --- the store against its own rebuild ----------------------------------------------------------


def _leaf(body: bytes) -> SimpleNamespace:
    """A leaf shaped like the wire messages, sealed-looking but arbitrary."""
    part = SimpleNamespace(
        encoding=0,
        encrypted=SimpleNamespace(nonce=b"n" * 12, tag=b"t" * 16, ct=body),
        plaintext=None,
    )
    identity = SimpleNamespace(
        key_type="address",
        encoding=0,
        encrypted=SimpleNamespace(nonce=b"i" * 12, tag=b"j" * 16, ct=b"id"),
        plaintext=None,
    )
    return SimpleNamespace(identity=identity, content=part)


def _commit(leaf: SimpleNamespace) -> bytes:
    return commit_of("address", leaf.identity, leaf.content)


def _keys(rng: random.Random, n: int, shared_prefix_bytes: int) -> list:
    prefix = bytes(rng.getrandbits(8) for _ in range(shared_prefix_bytes))
    return [
        prefix + bytes(rng.getrandbits(8) for _ in range(32 - shared_prefix_bytes))
        for _ in range(n)
    ]


@pytest.mark.parametrize("seed", range(6))
@pytest.mark.parametrize("shared_prefix_bytes", [0, 20])
def test_derived_roots_match_the_canonical_rebuild(
    seed: int, shared_prefix_bytes: int
) -> None:
    """Every insert/update/delete root the verifier derives equals the store's rebuilt root.

    `shared_prefix_bytes=20` makes keys agree on 160 bits, so splits land deep and inserts
    splice ABOVE existing branches -- the case that used to be wrong.
    """
    rng = random.Random(seed)
    keys = _keys(rng, 16, shared_prefix_bytes)
    store = WardTrie()
    root = EMPTY_ROOT

    for _step in range(300):
        key = rng.choice(keys)
        if key in store and rng.random() < 0.45:
            proof = store.membership_proof(key)
            root = delete_root(key, store.commit(key), proof, root)
            store.remove(key)
        elif key in store:
            new = _leaf(bytes([rng.getrandbits(8)]) * rng.randint(1, 5))
            proof = store.membership_proof(key)
            root = update_root(key, store.commit(key), _commit(new), proof, root)
            store.set(key, new)
        else:
            new = _leaf(bytes([rng.getrandbits(8)]) * rng.randint(1, 5))
            proof, wkey, wcommit = store.nonmembership_proof(key)
            root = insert_root(key, _commit(new), proof, root, wkey, wcommit)
            store.set(key, new)

        assert root == store.root_or_empty()
        assert store.root() == store.rebuild_root()  # the cache never drifts
        for k in store.blobs:
            assert verify_membership(k, store.commit(k), store.membership_proof(k), root)

    # drain to empty: every collapse, ending at EMPTY_ROOT, never None
    for key in sorted(store.blobs):
        root = delete_root(key, store.commit(key), store.membership_proof(key), root)
        store.remove(key)
        assert root == store.root_or_empty()
    assert root == EMPTY_ROOT and store.root() is None


def test_membership_proof_refuses_an_absent_key() -> None:
    store = WardTrie()
    store.set(MEMBER, _leaf(b"x"))
    with pytest.raises(KeyError):
        store.membership_proof(ABSENT)


def test_a_one_leaf_tree_has_the_leaf_as_its_root() -> None:
    store = WardTrie()
    leaf = _leaf(b"x")
    store.set(MEMBER, leaf)
    assert store.root() == leaf_hash(MEMBER, _commit(leaf))
    assert store.membership_proof(MEMBER) == []


def test_children_are_positional() -> None:
    left, right = bytes(32), bytes([1]) * 32
    assert internal_hash(0, left, right) != internal_hash(0, right, left)


# --- the transition log -----------------------------------------------------------------------


def _root(tag: str) -> bytes:
    import hashlib

    return hashlib.sha256(tag.encode()).digest()


def test_links_are_named_and_still_tuples() -> None:
    log = TransitionLog()
    link = log.record(0, None, 1, _root("a"), b"m" * 32, wm_sig=b"s")
    assert isinstance(link, Link) and isinstance(link, tuple)
    assert link[4] == link.auth_commit and link[:5] == tuple(link)[:5]
    assert link.operation == OP_COMMIT and log.wm_sigs[1] == b"s"
    with pytest.raises(ValueError):
        log.record(1, _root("a"), 2, _root("b"), b"m" * 32, operation="rewind")


def test_the_newest_link_into_a_state_wins() -> None:
    """A counter reached twice -- a write, then a REVERT -- serves the later edge."""
    r1, r2, r3 = _root("r1"), _root("r2"), _root("r3")
    log = TransitionLog()
    log.record(0, None, 1, r1, b"a" * 32)
    log.record(1, r1, 2, r2, b"b" * 32)
    log.record(2, r2, 3, r3, b"c" * 32)
    log.record(3, r3, 4, r1, b"d" * 32, operation=OP_REVERT)
    log.record(1, r1, 2, r2, b"e" * 32)  # the same step again, later
    assert log.links_ending_at(2, r2, limit=1)[0].auth_commit == b"e" * 32
    assert [lnk.to_counter for lnk in log.links_ending_at(4, r1)] == [4, 3, 2, 1]


def test_fork_point() -> None:
    r1, r2, r3a, r3b, r4 = (_root(t) for t in ("r1", "r2", "r3a", "r3b", "r4"))
    log = TransitionLog()
    for fc, fr, tc, tr in [
        (0, None, 1, r1),
        (1, r1, 2, r2),
        (2, r2, 3, r3a),
        (2, r2, 3, r3b),
        (3, r3b, 4, r4),
    ]:
        log.record(fc, fr, tc, tr, b"m" * 32)
    assert log.fork_point((3, r3a), (4, r4)) == 2
    assert log.fork_point((4, r4), (3, r3a)) == 2
    assert log.fork_point((2, r2), (4, r4)) == 2  # an ancestor: the lower head itself
    assert log.fork_point((3, _root("unknown")), (4, r4)) is None
