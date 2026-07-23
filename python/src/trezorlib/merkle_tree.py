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

import typing as t
from hashlib import sha256

from typing_extensions import Protocol


def leaf_hash(value: bytes) -> bytes:
    """Calculate a hash of a leaf node based on its value.

    See documentation for `MerkleTree` for details.
    """
    return sha256(b"\x00" + value).digest()


def internal_hash(left: bytes, right: bytes) -> bytes:
    """Calculate a hash of an internal node based on its child nodes.

    See documentation for `MerkleTree` for details.
    """
    hash_a = min(left, right)
    hash_b = max(left, right)
    return sha256(b"\x01" + hash_a + hash_b).digest()


class NodeType(Protocol):
    """Merkle tree node."""

    tree_hash: bytes
    """Merkle root hash of the subtree rooted at this node."""

    def add_to_proof_list(self, proof_entry: bytes) -> None:
        """Add a proof entry to the proof list of this node."""
        ...


class Leaf:
    """Leaf of a Merkle tree."""

    def __init__(self, value: bytes) -> None:
        self.tree_hash = leaf_hash(value)
        self.proof: t.List[bytes] = []

    def add_to_proof_list(self, proof_entry: bytes) -> None:
        self.proof.append(proof_entry)


class Node:
    """Internal node of a Merkle tree.

    Does not have its own proof, but helps to build the proof of its children by passing
    the respective proof entries to them.
    """

    def __init__(self, left: NodeType, right: NodeType) -> None:
        self.left = left
        self.right = right
        self.left.add_to_proof_list(self.right.tree_hash)
        self.right.add_to_proof_list(self.left.tree_hash)
        self.tree_hash = internal_hash(self.left.tree_hash, self.right.tree_hash)

    def add_to_proof_list(self, proof_entry: bytes) -> None:
        self.left.add_to_proof_list(proof_entry)
        self.right.add_to_proof_list(proof_entry)


class MerkleTree:
    """Merkle tree for a list of byte values.

    The leaves are ordered by their hash and the tree is built balanced: all leaves end
    up within one level of each other, so any two membership proofs differ in length by
    at most one. See `_build_tree` for details.

    Values are not saved in the tree, only their hashes. This allows us to construct a
    tree with very large values without having to keep them in memory.

    Semantically, the tree operates as a set, but this implementation does not check for
    duplicates. If the same value is added multiple times, the resulting tree will be
    different from a tree with only one instance of the value. In addition, only one of
    the several possible proofs for the repeated value is retrievable.

    Proof hashes are constructed as follows:

    - Leaf node entries are hashes of b"\x00" + value.
    - Internal node entries are hashes of b"\x01" + min(left, right) + max(left, right).

    The prefixes function to distinguish leaf nodes from internal nodes. This prevents
    two attacks:

    (a) An attacker cannot misuse a proof for an internal node to claim that
        <internal-node-entry> is a member of the tree.
    (b) An attacker cannot insert a leaf node in the format of <internal-node-entry>
        that is itself an internal node of a different tree. This would allow the
        attacker to expand the tree with their own subtree.

    Ordering the internal node entry as min(left, right) + max(left, right) simplifies
    the proof format and verifier code: when constructing the internal entry, the
    verifier does not need to distinguish between left and right subtree.
    """

    entries: t.Dict[bytes, Leaf]
    """Map of leaf hash -> leaf node.

    Use `leaf_hash` to calculate the hash of a value, or use `get_proof(value)`
    to access the proof directly.
    """
    root: NodeType
    """Root node of the tree."""

    def __init__(self, values: t.Iterable[bytes]) -> None:
        leaves = [Leaf(value) for value in values]

        if not leaves:
            raise ValueError("Merkle tree must have at least one value")

        leaves.sort(key=lambda leaf: leaf.tree_hash)
        self.entries = {leaf.tree_hash: leaf for leaf in leaves}
        self.root = self._build_tree(leaves)

    @staticmethod
    def _build_tree(leaves: t.Sequence[NodeType]) -> NodeType:
        """Build a balanced tree from an ordered sequence of leaves.

        The first leaves are pushed one level deeper so that the level above the bottom
        becomes a power of two; from there the tree is perfect. The deep leaves go first,
        so the last leaves get the shortest proofs.
        """
        if len(leaves) == 1:
            return leaves[0]

        # `depth` is ceil(log2(n)) and `capacity` the leaf count of a perfect tree of
        # that depth (the smallest power of two >= n). The first `split` leaves are
        # pushed one level deeper and paired up, so the level above the bottom becomes a
        # perfect power of two (`capacity // 2` wide); the remaining `n - split` leaves
        # stay shallow (shorter proofs).
        depth = (len(leaves) - 1).bit_length()
        capacity = 1 << depth
        split = 2 * len(leaves) - capacity
        level = [Node(leaves[i], leaves[i + 1]) for i in range(0, split, 2)] + list(
            leaves[split:]
        )

        # `level` now has a power-of-two length: collapse it into a perfect tree.
        while len(level) > 1:
            level = [Node(level[i], level[i + 1]) for i in range(0, len(level), 2)]
        return level[0]

    def get_root_hash(self) -> bytes:
        return self.root.tree_hash

    def get_proof(self, value: bytes) -> t.List[bytes]:
        """Get the proof for a given value."""
        try:
            return self.entries[leaf_hash(value)].proof
        except KeyError:
            raise KeyError("Value not found in Merkle tree") from None


def evaluate_proof(value: bytes, proof: t.List[bytes]) -> bytes:
    """Evaluate the provided proof of membership.

    Reconstructs the Merkle root hash for a tree that contains `value` as a leaf node,
    proving membership in a Merkle tree with the given root hash. The result can be
    compared to a statically known root hash, or a signature of it can be verified.
    """
    hash = leaf_hash(value)
    for proof_entry in proof:
        hash = internal_hash(hash, proof_entry)
    return hash
