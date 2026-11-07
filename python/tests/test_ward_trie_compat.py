"""Hash domains and byte vectors shared with the Rust WARD trie."""

import hashlib
import json
from pathlib import Path

from trezorlib import ward_crypto as wc
from trezorlib.authdb_tree import EMPTY_ROOT, WARDTree
from trezorlib.ward_protocol import root_bytes

VECTORS = json.loads(
    (
        Path(__file__).resolve().parents[2] / "common/tests/fixtures/ward/trie.json"
    ).read_text()
)


def _part(value):
    return wc.Part(
        value["encoding"],
        bytes.fromhex(value["nonceHex"]),
        bytes.fromhex(value["tagHex"]),
        bytes.fromhex(value["bodyHex"]),
    )


def test_default_value_hash_matches_rust_and_rejects_old_domain():
    tree = WARDTree()
    for row in VECTORS["leaves"]:
        key = bytes.fromhex(row["entryKeyHex"])
        leaf = wc.LeafBlob(
            row["keyType"], _part(row["identity"]), _part(row["content"])
        )
        value = bytes.fromhex(row["valueHex"])
        assert wc.leaf_value_bytes(leaf) == value
        assert wc.commit_of(leaf) == hashlib.sha256(b"\x03" + value).digest()
        assert wc.commit_of(leaf) != hashlib.sha256(b"\x02" + value).digest()
        tree.set_leaf(key, leaf)
    assert tree.get_root_hash().hex() == VECTORS["root"]
    for row in VECTORS["leaves"]:
        key = bytes.fromhex(row["entryKeyHex"])
        proof = tree.get_proof_by_key(key)
        leaf = tree.get_leaf(key)
        assert leaf is not None
        old_commit = hashlib.sha256(b"\x02" + wc.leaf_value_bytes(leaf)).digest()
        node = wc.leaf_hash_of(key, old_commit)
        for step in proof:
            bit = int.from_bytes(step[:2], "big")
            sibling = step[2:]
            left, right = (
                (node, sibling)
                if not (key[bit // 8] & (0x80 >> (bit % 8)))
                else (sibling, node)
            )
            node = hashlib.sha256(b"\x01" + step[:2] + left + right).digest()
        assert node != tree.get_root_hash()


def test_empty_root_matches_rust_including_after_last_delete():
    expected = bytes.fromhex(
        "dbc1b4c900ffe48d575b5da5c638040125f65db0fe3e24494b76ea986457d986"
    )
    tree = WARDTree()
    key = b"k" * 32
    assert EMPTY_ROOT == root_bytes("") == tree.get_root_hash() == expected
    leaf = wc.LeafBlob(
        "address", wc.Part(1, b"", b"", b"identity"), wc.Part(1, b"", b"", b"content")
    )
    assert (
        wc.commit_of(leaf).hex()
        == "d88beea6160625541876160d58dd0925f8e96397fad1af4d921fcb2c9f6a647a"
    )
    tree.set_leaf(key, leaf)
    tree.del_leaf(key)
    assert tree.get_root_hash() == expected
    assert WARDTree.verify_nonmembership_by_key(key, None, None, [], expected)
    assert not WARDTree.verify_nonmembership_by_key(
        key, None, None, [], hashlib.sha256(b"\x03").digest()
    )
