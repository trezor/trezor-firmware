from typing import Any, Optional, Tuple

from .library import dumps, hexlify, loads, sha256, unhexlify
from .patricia_merkle_trie import (
    BranchNode,
    DigestNode,
    Node,
    PatriciaMerkleTrie,
    Value,
    ValueNode,
)


def encode_key(key: str) -> Tuple[bool, ...]:
    def bytes_to_bits(data: bytes) -> Tuple[bool, ...]:
        def get_bit(data: bytes, i: int) -> bool:
            return data[i // 8] & (1 << (i % 8)) != 0

        return tuple([get_bit(data, i) for i in range(len(data) * 8)])

    return bytes_to_bits(sha256(key.encode()).digest())


def encode_value(value: str) -> bytes:
    return value.encode()


def encode_optional_value(value: Optional[str]) -> Optional[Value]:
    if value is None:
        return None
    return encode_value(value)


def decode_value(value: Value) -> str:
    return value.decode()


def decode_optional_value(value: Optional[Value]) -> Optional[str]:
    if value is None:
        return None
    return decode_value(value)


class DigestPatriciaMerkleTrie:
    def __init__(self, root: Optional[PatriciaMerkleTrie] = None):
        if root is not None:
            self.root = root
        else:
            self.root = PatriciaMerkleTrie()

    def search(self, key: str) -> Optional[str]:
        return decode_optional_value(self.root.search(encode_key(key)))

    def modify(self, key: str, value: Optional[str]) -> None:
        self.root.modify(encode_key(key), encode_optional_value(value))

    def compute_digest(self) -> bytes:
        return self.root.compute_digest()

    def generate_membership_proof(
        self, key: str
    ) -> Tuple["DigestPatriciaMerkleTrie", Optional[str]]:
        proof, value = self.root.generate_membership_proof(encode_key(key))
        return DigestPatriciaMerkleTrie(proof), decode_optional_value(value)

    def generate_modification_proof(
        self, key: str, value: Optional[str]
    ) -> "DigestPatriciaMerkleTrie":
        return DigestPatriciaMerkleTrie(
            self.root.generate_modification_proof(
                encode_key(key), encode_optional_value(value)
            )
        )

    def verify_proof(
        self,
        digest: bytes,
        key: str,
        value: Optional[str],
    ) -> bool:
        return self.root.verify_proof(
            digest, encode_key(key), encode_optional_value(value)
        )

    def open_proof(self, key: str, digest: bytes) -> Optional[str]:
        return decode_optional_value(self.root.open_proof(encode_key(key), digest))

    def to_json(self) -> Any:
        def digest_node_to_json(node: DigestNode) -> Any:
            return {"type": "digest", "digest": hexlify(node.digest)}

        def value_node_to_json(node: ValueNode) -> Any:
            return {
                "type": "value",
                "prefix": node.prefix,
                "value": node.value.decode(),
            }

        def branch_node_to_json(node: BranchNode) -> Any:
            children = []
            for direction, child in node.children.items():
                children.append({"direction": direction, "child": to_json_inner(child)})
            return {"type": "branch", "prefix": node.prefix, "children": children}

        def to_json_inner(node: Node) -> Any:
            if isinstance(node, DigestNode):
                return digest_node_to_json(node)
            if isinstance(node, ValueNode):
                return value_node_to_json(node)
            if isinstance(node, BranchNode):
                return branch_node_to_json(node)

        if self.root.root is None:
            return None
        return to_json_inner(self.root.root)

    @classmethod
    def from_json(cls, data: Any) -> "DigestPatriciaMerkleTrie":
        def digest_node_from_json(data: Any) -> DigestNode:
            return DigestNode(unhexlify(data["digest"]))

        def value_node_from_json(data: Any) -> ValueNode:
            return ValueNode(tuple(data["prefix"]), encode_value(data["value"]))

        def branch_node_from_json(data: Any) -> BranchNode:
            children = {}
            for child in data["children"]:
                children[child["direction"]] = from_json_inner(child["child"])
            return BranchNode(tuple(data["prefix"]), children)

        def from_json_inner(data: Any) -> Node:
            if data["type"] == "digest":
                return digest_node_from_json(data)
            if data["type"] == "value":
                return value_node_from_json(data)
            if data["type"] == "branch":
                return branch_node_from_json(data)
            raise ValueError("Invalid node type")

        trie = DigestPatriciaMerkleTrie()
        if data is not None:
            trie.root.root = from_json_inner(data)
        return trie

    def to_bytes(self) -> bytes:
        return dumps(self.to_json()).encode()

    @classmethod
    def from_bytes(cls, data: bytes) -> "DigestPatriciaMerkleTrie":
        return cls.from_json(loads(data))
