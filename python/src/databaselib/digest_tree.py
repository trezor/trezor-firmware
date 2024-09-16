from typing import Any, Optional, Tuple

from . import tree
from .library import dumps, loads, sha256
from .tree import BranchNode, DigestNode, Tree, ValueNode


def encode_key(key: str) -> Tuple[bool, ...]:
    def bytes_to_bits(data: bytes) -> Tuple[bool, ...]:
        def get_bit(data: bytes, i: int) -> bool:
            return data[i // 8] & (1 << (i % 8)) != 0

        return tuple([get_bit(data, i) for i in range(len(data) * 8)])

    return bytes_to_bits(sha256(key.encode()).digest())


def encode_value(value: str) -> bytes:
    return value.encode()


def encode_optional_value(value: Optional[str]) -> Optional[bytes]:
    if value is None:
        return None
    return encode_value(value)


def decode_value(value: bytes) -> str:
    return value.decode()


def decode_optional_value(value: Optional[bytes]) -> Optional[str]:
    if value is None:
        return None
    return decode_value(value)


def insert(tree_root: Tree, key: str, value: str) -> bool:
    if search(tree_root, key) is not None:
        tree.change(tree_root, encode_key(key), encode_value(value))
    return tree.insert(tree_root, encode_key(key), encode_value(value))


def from_json(data: Any) -> Tree:
    return tree.from_json(data)


def to_json(tree_root: Tree) -> Any:
    return tree.to_json(tree_root)


def generate_insert_proof(tree_root: Tree, key: str) -> Tree:
    return tree.generate_insert_proof(tree_root, encode_key(key))


def empty() -> Tree:
    return tree.empty()


def generate_memoof(tree_root: Tree, key: str) -> Tree:
    return tree.generate_insert_proof(tree_root, encode_key(key))


def generate_membership_proof(root_tree: Tree, key: str) -> Tuple[Tree, Optional[str]]:
    proof, value = tree.generate_membership_proof(root_tree, encode_key(key))
    return proof, decode_optional_value(value)


def compute_hash(root_tree: ValueNode | Tree | BranchNode | DigestNode) -> bytes:
    return tree.compute_hash(root_tree)


def verify_proof(
    root_digest: bytes,
    key: str,
    value: Optional[str],
    proof: Tree,
) -> bool:
    return tree.verify_proof(
        root_digest, encode_key(key), encode_optional_value(value), proof
    )


def search(root_tree: Tree, key: str) -> Optional[str]:
    return decode_optional_value(tree.search(root_tree, encode_key(key)))


def to_bytes(tree_root: Tree) -> bytes:
    return dumps(tree.to_json(tree_root)).encode()


def from_bytes(data: bytes) -> Tree:
    return tree.from_json(loads(data.decode()))
