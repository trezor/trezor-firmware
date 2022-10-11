from typing import Optional

try:
    from trezor.crypto.hashlib import sha256
except ImportError:
    from hashlib import sha256


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
        self.is_leaf = raw_value is not None
        self.raw_value = raw_value

        if self.is_leaf and (left is not None or right is not None):
            raise ValueError(
                "Cannot use `raw_value` together with `left` and/or `right` value."
            )

        self.hash = None
        self.left_child = left
        self.right_child = right
        self.proof_list: list[bytes] = []

    def compute_hash(self) -> bytes:
        if not self.hash:
            if self.is_leaf:
                self.hash = sha256(b"\x00" + self.raw_value).digest()
            else:
                left_hash = self.left_child.compute_hash()
                right_hash = self.right_child.compute_hash()
                hash_a = min(left_hash, right_hash)
                hash_b = max(left_hash, right_hash)
                self.hash = sha256(b"\x01" + hash_a + hash_b).digest()

                # distribute proof
                self.left_child.add_to_proof(right_hash)
                self.right_child.add_to_proof(left_hash)

        return self.hash

    def add_to_proof(self, proof: bytes) -> None:
        self.proof_list.append(proof)
        if not self.is_leaf:
            self.left_child.add_to_proof(proof)
            self.right_child.add_to_proof(proof)


class MerkleTree:
    """
    Simple Merkle tree that implements the building of Merkle tree itself and generate proofs
    for leaf nodes.
    """

    def __init__(self, values: list[bytes]) -> None:
        self.leaves = [Node(raw_value=v) for v in values]

        # build the tree
        actual_level = [n for n in self.leaves]
        while len(actual_level) > 1:
            # build one level of the tree
            next_level = []
            while len(actual_level) // 2:
                left_node = actual_level.pop(0)
                right_node = actual_level.pop(0)
                next_level.append(Node(left=left_node, right=right_node))

            if len(actual_level) == 1:
                # odd number of nodes on actual level so last node will be "joined" on another level
                next_level.append(actual_level.pop(0))

            # switch levels and continue
            actual_level = next_level

        # set root and compute hash
        self.root_node = actual_level[0]
        self.root_node.compute_hash()

    def get_proofs(self) -> dict[bytes, list[bytes]]:
        return {n.raw_value: n.proof_list for n in self.leaves}

    def get_root_hash(self) -> bytes:
        return self.root_node.hash
