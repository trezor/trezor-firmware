from typing import Any, Dict, List, Optional, Tuple, Union

from .library import hexlify, sha256

Value = bytes
Alphabeth = int
Key = Tuple[Alphabeth, ...]  # TODO: rename to Key


class ValueNode:
    def __init__(self, prefix: Key, value: Value):
        self.prefix = prefix
        self.value = value

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, ValueNode):
            return False
        return self.prefix == other.prefix and self.value == other.value


class BranchNode:
    def __init__(self, prefix: Key, children: Dict[Alphabeth, "Node"]):
        self.prefix = prefix
        self.children = children

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, BranchNode):
            return False
        return self.prefix == other.prefix and self.children == other.children


class DigestNode:
    def __init__(self, digest: bytes):
        self.digest = digest

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, DigestNode):
            return False
        return self.digest == other.digest

    def clone(self) -> "DigestNode":
        return DigestNode(digest=self.digest)


Node = Union[ValueNode, BranchNode, DigestNode]


def find_common_prefix(first: Key, second: Key) -> Key:
    prefix = []
    for f, s in zip(first, second):
        if f != s:
            break
        prefix.append(f)
    return tuple(prefix)


class PatriciaMerkleTrie:
    def __init__(self, root: Optional[Node] = None):
        self.root: Optional[Node] = root

    def get_brother(self, node: Node, parent: BranchNode) -> Node:
        for child in parent.children.values():
            if child != node:
                return child
        assert False  # TODO

    def find_path(self, key: Key) -> Tuple[
        Tuple[Node, ...],
        Key,
    ]:
        if self.root is None:
            # the tree is empty
            return (), key

        assert isinstance(self.root, ValueNode) or isinstance(self.root, BranchNode)

        node: ValueNode | BranchNode = self.root
        remaining_key = key
        path: List[ValueNode | BranchNode] = []

        while True:
            assert isinstance(node, ValueNode) or isinstance(node, BranchNode)
            path.append(node)

            if remaining_key[: len(node.prefix)] != node.prefix:
                # the key is not in the tree
                # the key and the path to the node have a common prefix
                break

            remaining_key = remaining_key[len(node.prefix) :]
            if remaining_key == ():
                # the key is in the tree
                break

            # Inner value nodes are not allowed
            assert isinstance(node, BranchNode)

            new_node = node.children[remaining_key[0]]  # TODO: inline variable
            assert isinstance(new_node, BranchNode) or isinstance(new_node, ValueNode)
            node = new_node

        return tuple(path), remaining_key

    def search_inner(
        self, path: Tuple[Node, ...], remaining_key: Key
    ) -> Optional[Value]:
        if path == ():
            # the tree is empty
            return None

        if remaining_key:
            # the key is not in the tree
            return None

        node = path[-1]
        assert isinstance(node, ValueNode)
        return node.value

    def search(self, key: Key) -> Optional[Value]:
        path, remaining_key = self.find_path(key)
        return self.search_inner(path, remaining_key)

    def insert_inner(
        self, path: Tuple[Node, ...], remaining_key: Key, value: Value
    ) -> bool:
        if self.root is None:
            # the tree is empty
            self.root = ValueNode(prefix=remaining_key, value=value)
            return True

        if not remaining_key:
            # the key is already in the tree
            return False

        node = path[-1]
        assert isinstance(node, ValueNode) or isinstance(node, BranchNode)

        common_prefix = find_common_prefix(node.prefix, remaining_key)

        node.prefix = node.prefix[len(common_prefix) :]

        new_value_node: ValueNode = ValueNode(
            prefix=remaining_key[len(common_prefix) :], value=value
        )

        new_branch_node: BranchNode = BranchNode(
            prefix=common_prefix,
            children={
                node.prefix[0]: node,
                new_value_node.prefix[0]: new_value_node,
            },
        )

        if len(path) == 1:
            self.root = new_branch_node
        else:
            parent = path[-2]
            assert isinstance(parent, BranchNode)
            parent.children[new_branch_node.prefix[0]] = new_branch_node

        return True

    def insert(self, key: Key, value: Value) -> bool:
        path, remaining_key = self.find_path(key)
        return self.insert_inner(path, remaining_key, value)

    def delete_inner(self, path: Tuple[Node, ...], remaining_key: Key) -> bool:
        if self.root is None:
            # the tree is empty
            return False

        if remaining_key:
            # the key is not in the tree
            return False

        node = path[-1]
        assert isinstance(node, ValueNode)

        if len(path) == 1:
            # the tree has a single element
            self.root = None
            return True

        parent = path[-2]
        assert isinstance(parent, BranchNode)

        brother = self.get_brother(node, parent)
        assert isinstance(brother, BranchNode) or isinstance(brother, ValueNode)
        brother.prefix = parent.prefix + brother.prefix

        if len(path) == 2:
            self.root = brother
            return True
        else:
            grand_parent = path[-3]
            assert isinstance(grand_parent, BranchNode)
            grand_parent.children[brother.prefix[0]] = brother

        return True

    def delete(self, key: Key) -> bool:
        path, remaining_key = self.find_path(key)
        return self.delete_inner(path, remaining_key)

    def modify(self, key: Key, value: Optional[Value]) -> None:
        path, remaining_key = self.find_path(key)
        if value is None:
            self.delete_inner(path, remaining_key)
        elif remaining_key:
            self.insert_inner(path, remaining_key, value)
        else:
            node = path[-1]
            assert isinstance(node, ValueNode)
            node.value = value

    def draw(self) -> None:
        base_indent = "  "

        def draw_inner(node: ValueNode | BranchNode | DigestNode, depth: int):
            if isinstance(node, ValueNode):
                print(
                    f"{base_indent * depth}ValueNode({node.prefix}, {node.value.decode()})"
                )
            if isinstance(node, BranchNode):
                print(f"{base_indent * depth}BranchNode({node.prefix})")
                for child in node.children.values():
                    draw_inner(child, depth + 1)
            if isinstance(node, DigestNode):
                print(
                    f"{base_indent * depth}DigestNode({hexlify(node.digest).decode()})"
                )

        print("Root")
        if self.root is not None:
            draw_inner(self.root, 1)

    def __eq__(self, other: Any) -> bool:
        return self.root == other.root

    def compute_digest(self, node: Optional[Node] = None) -> bytes:
        branch_node_prefix = b"\x01"
        value_node_prefix = b"\x02"

        def prefix_by_length(data: bytes) -> bytes:
            return len(data).to_bytes(4, "big") + data

        def value_node_compute_digest(node: ValueNode) -> bytes:
            context = sha256()
            context.update(value_node_prefix)
            context.update(prefix_by_length(bytes(node.prefix)))
            context.update(prefix_by_length(node.value))
            return context.digest()

        def branch_node_compute_digest(node: BranchNode) -> bytes:
            context = sha256()
            context.update(branch_node_prefix)
            context.update(prefix_by_length(bytes(node.prefix)))
            for direction, child in sorted(node.children.items(), key=lambda x: x[0]):
                context.update(self.compute_digest(child))
            return context.digest()

        def digest_node_compute_digest(node: DigestNode) -> bytes:
            return node.digest

        if self.root is None:
            # the tree is empty
            return bytes(32)

        if node is None:
            node = self.root

        if isinstance(node, ValueNode):
            return value_node_compute_digest(node)
        if isinstance(node, BranchNode):
            return branch_node_compute_digest(node)
        if isinstance(node, DigestNode):
            return digest_node_compute_digest(node)

    def to_digest_tree(self, nodes: Tuple[Node, ...]) -> "PatriciaMerkleTrie":
        def to_digest_tree_inner(
            node: Node,
            nodes: Tuple[Node, ...],
        ) -> Node:
            def value_node_clone(self) -> ValueNode:
                return ValueNode(prefix=self.prefix, value=self.value)

            def branch_node_clone(self) -> BranchNode:
                children = {}
                for direction, child in self.children.items():
                    children[direction] = to_digest_tree_inner(child, nodes)
                return BranchNode(prefix=self.prefix, children=children)

            if node not in nodes:
                return DigestNode(digest=self.compute_digest(node))
            if isinstance(node, ValueNode):
                return value_node_clone(node)
            if isinstance(node, BranchNode):
                return branch_node_clone(node)
            raise AssertionError("Unreachable code.")

        if self.root is None:
            return PatriciaMerkleTrie(root=None)
        return PatriciaMerkleTrie(to_digest_tree_inner(self.root, nodes))
        Key

    def generate_membership_proof(
        self, key: Key
    ) -> Tuple["PatriciaMerkleTrie", Optional[Value]]:
        path, remaining_key = self.find_path(key)
        digest_tree = self.to_digest_tree(path)
        return digest_tree, self.search_inner(path, remaining_key)

    def generate_insertion_proof_inner(
        self, path: Tuple[Node, ...], remaining_key: Key
    ) -> "PatriciaMerkleTrie":
        assert remaining_key != ()

        if len(path) >= 2:
            if isinstance(path[-1], BranchNode):
                path = path + (path[-1].children[remaining_key[0]],)

        digest_tree = self.to_digest_tree(path)
        return digest_tree

    def generate_insertion_proof(self, key: Key) -> "PatriciaMerkleTrie":
        path, remaining_key = self.find_path(key)
        return self.generate_insertion_proof_inner(path, remaining_key)

    def generate_deletion_proof_inner(
        self, path: Tuple[Node, ...], remaining_key: Key
    ) -> "PatriciaMerkleTrie":
        assert remaining_key == ()

        if len(path) >= 2:
            assert isinstance(path[-2], BranchNode)
            path = path + (self.get_brother(path[-1], path[-2]),)

        digest_tree = self.to_digest_tree(path)
        return digest_tree

    def generate_deletion_proof(self, key: Key) -> "PatriciaMerkleTrie":
        path, remaining_key = self.find_path(key)
        return self.generate_deletion_proof_inner(path, remaining_key)

    def generate_change_proof_inner(
        self, path: Tuple[Node, ...], remaining_key: Key
    ) -> "PatriciaMerkleTrie":
        digest_tree = self.to_digest_tree(path)
        return digest_tree

    def generate_change_proof(self, key: Key) -> "PatriciaMerkleTrie":
        path, remaining_key = self.find_path(key)
        return self.generate_change_proof_inner(path, remaining_key)

    def generate_modification_proof(
        self, key: Key, value: Optional[Value]
    ) -> "PatriciaMerkleTrie":
        path, remaining_key = self.find_path(key)
        found_value = self.search_inner(path, remaining_key)
        if value is None and found_value is not None:
            return self.generate_deletion_proof_inner(path, remaining_key)
        if value is not None and found_value is None:
            return self.generate_insertion_proof_inner(path, remaining_key)
        if value is not None and found_value is not None:
            return self.generate_change_proof_inner(path, remaining_key)
        raise AssertionError("Unreachable code.")

    def verify_proof(
        self,
        digest: bytes,
        key: Key,
        value: Optional[Value],
    ) -> bool:
        if self.compute_digest() != digest:
            return False
        return self.search(key) == value

    def open_proof(
        self,
        key: Key,
        digest: bytes,
    ) -> Optional[Value]:
        if self.compute_digest() != digest:
            raise ValueError("Invalid proof.")
        return self.search(key)
