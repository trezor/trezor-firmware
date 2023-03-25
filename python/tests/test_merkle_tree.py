# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
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

import typing as t

import pytest

from trezorlib.merkle_tree import (
    Leaf,
    MerkleTree,
    Node,
    evaluate_proof,
    internal_hash,
    leaf_hash,
)

NODE_VECTORS = (  # node, expected_hash
    (  # leaf node
        Leaf(b"hello"),
        "8a2a5c9b768827de5a9552c38a044c66959c68f6d2f21b5260af54d2f87db827",
    ),
    (  # node with leaf nodes
        Node(left=Leaf(b"hello"), right=Leaf(b"world")),
        "24233339aadcedf287d262413f03c028eb8db397edd32a2878091151b99bf20f",
    ),
    (  # asymmetric node with leaf hanging on second level
        Node(left=Node(left=Leaf(b"hello"), right=Leaf(b"world")), right=Leaf(b"!")),
        "c3727420dc97c0dbd89678ee195957e44cfa69f5759b395a07bc171b21468633",
    ),
)


MERKLE_TREE_VECTORS = (
    (  # one value
        # values
        [b"Merkle"],
        # expected root hash
        leaf_hash(b"Merkle"),
        # expected dict of proof lists
        {
            b"Merkle": [],
        },
    ),
    (  # two values
        # values
        [b"Haber", b"Stornetta"],
        # expected root hash
        internal_hash(
            leaf_hash(b"Haber"),
            leaf_hash(b"Stornetta"),
        ),
        # expected dict of proof lists
        {
            b"Haber": [leaf_hash(b"Stornetta")],
            b"Stornetta": [leaf_hash(b"Haber")],
        },
    ),
    (  # three values
        # values
        [b"Andersen", b"Wuille", b"Maxwell"],
        # expected root hash
        internal_hash(
            internal_hash(
                leaf_hash(b"Maxwell"),
                leaf_hash(b"Wuille"),
            ),
            leaf_hash(b"Andersen"),
        ),
        # expected dict of proof lists
        {
            b"Andersen": [internal_hash(leaf_hash(b"Maxwell"), leaf_hash(b"Wuille"))],
            b"Maxwell": [leaf_hash(b"Wuille"), leaf_hash(b"Andersen")],
            b"Wuille": [leaf_hash(b"Maxwell"), leaf_hash(b"Andersen")],
        },
    ),
)


@pytest.mark.parametrize("node, expected_hash", NODE_VECTORS)
def test_node(node: t.Union[Node, Leaf], expected_hash: str) -> None:
    assert node.tree_hash.hex() == expected_hash


@pytest.mark.parametrize("values, root_hash, proofs", MERKLE_TREE_VECTORS)
def test_tree(
    values: t.List[bytes],
    root_hash: bytes,
    proofs: t.Dict[bytes, t.List[bytes]],
) -> None:
    mt = MerkleTree(values)
    assert mt.get_root_hash() == root_hash
    for value, proof in proofs.items():
        assert mt.get_proof(value) == proof
        assert evaluate_proof(value, proof) == root_hash
