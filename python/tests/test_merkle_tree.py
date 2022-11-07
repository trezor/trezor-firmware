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

import pytest

from hashlib import sha256
from typing import Dict, List

from trezorlib.merkle_tree import MerkleTree, Node


NODE_VECTORS = (
    (  # leaf node
        # node
        Node(
            raw_value=bytes.fromhex("dead"),
        ),
        # expected hash
        sha256(b"\x00" + bytes.fromhex("dead")).digest()
    ),
    (  # node with leaf nodes
        # node
        Node(
            left=Node(
                raw_value=bytes.fromhex("dead"),
            ),
            right=Node(
                raw_value=bytes.fromhex("beef"),
            ),
        ),
        # expected hash
        sha256(
            b"\x01"
            + sha256(b"\x00" + bytes.fromhex("beef")).digest()
            + sha256(b"\x00" + bytes.fromhex("dead")).digest()
        ).digest()
    ),
    (  # node with parent node (left)
        # node
        Node(
            left=Node(
                raw_value=bytes.fromhex("dead"),
            ),
            right=Node(
                raw_value=bytes.fromhex("beef"),
            ),
        ).left_child,
        # expected hash
        sha256(b"\x00" + bytes.fromhex("dead")).digest()
    ),
    (  # node with parent node (right)
        # node
        Node(
            left=Node(
                raw_value=bytes.fromhex("dead"),
            ),
            right=Node(
                raw_value=bytes.fromhex("beef"),
            ),
        ).right_child,
        # expected hash
        sha256(b"\x00" + bytes.fromhex("beef")).digest()
    ),
)


NODE_FAILED_VECTORS = (
    (  # no inputs
        # left
        None,
        # right
        None,
        # raw_value
        None,
    ),
    (  # only left child
        # left
        Node(raw_value=bytes.fromhex("dead")),
        # right
        None,
        # raw_value
        None,
    ),
    (  # only right child
        # left
        None,
        # right
        Node(raw_value=bytes.fromhex("beef")),
        # raw_value
        None,
    ),
    (  # all inputs
        # left
        Node(raw_value=bytes.fromhex("dead")),
        # right
        Node(raw_value=bytes.fromhex("beef")),
        # raw_value
        bytes.fromhex("deadbeef"),
    ),
)

MERKLE_TREE_VECTORS = (
    (  # one value
        # values
        [bytes.fromhex("dead")],
        # expected root hash
        sha256(b"\x00" + bytes.fromhex("dead")).digest(),
        # expected tree height
        0,
        # expected dict of proof lists
        {
            bytes.fromhex("dead"): [],
        },
    ),
    (  # two values
        # values
        [bytes.fromhex("dead"), bytes.fromhex("beef")],
        # expected root hash
        sha256(
            b"\x01"
            + sha256(b"\x00" + bytes.fromhex("beef")).digest()
            + sha256(b"\x00" + bytes.fromhex("dead")).digest()
        ).digest(),
        # expected tree height
        1,
        # expected dict of proof lists
        {
            bytes.fromhex("dead"): [sha256(b"\x00" + bytes.fromhex("beef")).digest()],
            bytes.fromhex("beef"): [sha256(b"\x00" + bytes.fromhex("dead")).digest()],
        },
    ),
    (  # three values
        # values
        [bytes.fromhex("dead"), bytes.fromhex("beef"), bytes.fromhex("cafe")],
        # expected root hash
        sha256(
            b"\x01"
            + sha256(
                b"\x01"
                + sha256(b"\x00" + bytes.fromhex("cafe")).digest()
                + sha256(b"\x00" + bytes.fromhex("beef")).digest()
            ).digest()
            + sha256(b"\x00" + bytes.fromhex("dead")).digest()
        ).digest(),
        # expected tree height
        2,
        # expected dict of proof lists
        {
            bytes.fromhex("dead"): [
                sha256(
                    b"\x01"
                    + sha256(b"\x00" + bytes.fromhex("cafe")).digest()
                    + sha256(b"\x00" + bytes.fromhex("beef")).digest()
                ).digest()
            ],
            bytes.fromhex("beef"): [
                sha256(b"\x00" + bytes.fromhex("cafe")).digest(),
                sha256(b"\x00" + bytes.fromhex("dead")).digest()
            ],
            bytes.fromhex("cafe"): [
                sha256(b"\x00" + bytes.fromhex("beef")).digest(),
                sha256(b"\x00" + bytes.fromhex("dead")).digest()
            ],
        },
    ),
)

MERKLE_TREE_FAILED_VECTORS = (
    (  # no values
        # values
        [],
    ),
)


@pytest.mark.parametrize("node, expected_hash", NODE_VECTORS)
def test_node(node: Node, expected_hash: bytes) -> None:
    assert node.compute_hash() == expected_hash
    assert node.get_hash() == expected_hash


@pytest.mark.parametrize("left, right, raw_value", NODE_FAILED_VECTORS)
def test_node_failed(left: Node, right: Node, raw_value: bytes) -> None:
    with pytest.raises(ValueError):
        Node(
            left=left,
            right=right,
            raw_value=raw_value,
        )


@pytest.mark.parametrize("values, expected_root_hash, expected_height, expected_proofs", MERKLE_TREE_VECTORS)
def test_tree(values: List[bytes], expected_root_hash: bytes, expected_height: int, expected_proofs: Dict[bytes, List[bytes]]) -> None:
    mt = MerkleTree(values)
    assert mt.get_root_hash() == expected_root_hash
    assert mt.get_tree_height() == expected_height
    assert mt.get_proofs() == expected_proofs


@pytest.mark.parametrize("values", MERKLE_TREE_FAILED_VECTORS)
def test_tree_failed(values: List[bytes]) -> None:
    with pytest.raises(ValueError):
        MerkleTree(values)
