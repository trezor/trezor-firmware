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

from hashlib import sha256
from typing import Dict, List, Optional


class Node:
    """
    Single node of Merkle tree.
    """

    def __init__(
        self: "Node",
        *,
        left: Optional["Node"] = None,
        right: Optional["Node"] = None,
        raw_value: Optional[bytes] = None,
    ) -> None:
        self.raw_value = raw_value

        if self.raw_value and (left is not None or right is not None):
            raise ValueError(
                "Cannot use `raw_value` together with `left` and/or `right` value."
            )

        if not self.raw_value and (left is None or right is None):
            raise ValueError(
                "`left` and `right` value must not be None when not using `raw_value`."
            )

        self.hash = None
        self.left_child = left
        self.right_child = right
        self.proof_list: List[bytes] = []

    def compute_hash(self) -> bytes:
        if not self.hash:
            if self.raw_value:
                self.hash = sha256(b"\x00" + self.raw_value).digest()
            else:
                left_hash = self.left_child.compute_hash()  # type: ignore ["compute_hash" is not a known member of "None"]
                right_hash = self.right_child.compute_hash()  # type: ignore ["compute_hash" is not a known member of "None"]
                hash_a = min(left_hash, right_hash)
                hash_b = max(left_hash, right_hash)
                self.hash = sha256(b"\x01" + hash_a + hash_b).digest()

                # distribute proof
                self.left_child.add_to_proof(right_hash)  # type: ignore ["add_to_proof" is not a known member of "None"]
                self.right_child.add_to_proof(left_hash)  # type: ignore ["add_to_proof" is not a known member of "None"]

        return self.hash

    def add_to_proof(self, proof: bytes) -> None:
        self.proof_list.append(proof)
        if not self.raw_value:
            self.left_child.add_to_proof(proof)  # type: ignore ["add_to_proof" is not a known member of "None"]
            self.right_child.add_to_proof(proof)  # type: ignore ["add_to_proof" is not a known member of "None"]


class MerkleTree:
    """
    Simple Merkle tree that implements the building of Merkle tree itself and generate proofs
    for leaf nodes.
    """

    def __init__(self, values: List[bytes]) -> None:
        self.leaves = [Node(raw_value=v) for v in values]
        self.height = 0

        # build the tree
        current_level = [n for n in self.leaves]
        while len(current_level) > 1:
            # build one level of the tree
            next_level = []
            while len(current_level) // 2:
                left_node = current_level.pop()
                right_node = current_level.pop()
                next_level.append(Node(left=left_node, right=right_node))

            if len(current_level) == 1:
                # odd number of nodes on current level so last node will be "joined" on another level
                next_level.append(current_level.pop())

            # switch levels and continue
            self.height += 1
            current_level = next_level

        # set root and compute hash
        self.root_node = current_level[0]
        self.root_node.compute_hash()

    def get_proofs(self) -> Dict[bytes, List[bytes]]:
        return {
            n.raw_value: n.proof_list for n in self.leaves if n.raw_value is not None
        }

    def get_tree_height(self) -> int:
        return self.height

    def get_root_hash(self) -> bytes:
        return self.root_node.hash  # type: ignore [Expression of type "bytes | None" cannot be assigned to return type "bytes"]
