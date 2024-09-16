from binascii import unhexlify
from typing import Any, Dict, List, Optional, Tuple

# TODO
try:
    from trezor.crypto.hashlib import sha256
except ImportError:
    from hashlib import sha256

Value = bytes
Alphabeth = bool
Path = Tuple[Alphabeth, ...]


def find_common_prefix(first: Path, second: Path) -> Path:
    prefix = []
    for f, s in zip(first, second):
        if f != s:
            break
        prefix.append(f)
    return tuple(prefix)


class ValueNode:
    def __init__(self, prefix: Path, value: Value):
        self.prefix = prefix
        self.value = value


class BranchNode:
    def __init__(self, prefix: Path, children: Dict[Alphabeth, "Node"]):
        self.prefix = prefix
        self.children = children


class DigestNode:
    def __init__(self, digest: bytes):
        self.digest = digest


try:
    Node = ValueNode | BranchNode | DigestNode
except Exception:
    pass


class Tree:
    def __init__(self, child: Optional[ValueNode | BranchNode | DigestNode] = None):
        self.child = child


def compute_hash(tree: ValueNode | Tree | BranchNode | DigestNode) -> bytes:
    root_node_prefix = b"\x00"
    branch_node_prefix = b"\x01"
    value_node_prefix = b"\x02"

    def prefix_length(data: bytes) -> bytes:
        return len(data).to_bytes(4, "big") + data

    def root_node_hash(node: Tree) -> bytes:
        context = sha256()
        context.update(root_node_prefix)
        if node.child is not None:
            context.update(compute_hash(node.child))
        return context.digest()

    def value_node_hash(node: ValueNode) -> bytes:
        context = sha256()
        context.update(value_node_prefix)
        context.update(prefix_length(bytes(node.prefix)))
        context.update(prefix_length(node.value))
        return context.digest()

    def branch_node_hash(node: BranchNode) -> bytes:
        context = sha256()
        context.update(branch_node_prefix)
        context.update(prefix_length(bytes(node.prefix)))
        for direction, child in sorted(node.children.items(), key=lambda x: x[0]):
            context.update(compute_hash(child))
        return context.digest()

    def digest_node_hash(node: DigestNode) -> bytes:
        return node.digest

    if isinstance(tree, Tree):
        return root_node_hash(tree)
    if isinstance(tree, ValueNode):
        return value_node_hash(tree)
    if isinstance(tree, BranchNode):
        return branch_node_hash(tree)
    if isinstance(tree, DigestNode):
        return digest_node_hash(tree)


def empty() -> Tree:
    return Tree(child=None)


def get_brother(
    node: ValueNode | BranchNode | DigestNode, parent: BranchNode
) -> ValueNode | BranchNode | DigestNode:
    for child in parent.children.values():
        if child != node:
            return child
    assert False


def find_path(tree: Tree, key: Path) -> Tuple[
    Tuple[Node | Tree, ...],
    Path,
]:
    node: ValueNode | BranchNode | Tree = tree
    remaining_key = key
    path: List[ValueNode | BranchNode | Tree] = [node]

    if tree.child is None:
        # the tree is empty
        return tuple(path), remaining_key

    assert isinstance(tree.child, ValueNode) or isinstance(tree.child, BranchNode)
    node = tree.child

    while True:
        assert isinstance(node, ValueNode) or isinstance(node, BranchNode)
        path.append(node)

        # TODO: digest tree

        if remaining_key[: len(node.prefix)] != node.prefix:
            # the key is not in the tree
            # the key and the path to the node have a common prefix
            break

        remaining_key = remaining_key[len(node.prefix) :]
        if remaining_key == ():
            # the key is in the tree
            break

        assert isinstance(node, BranchNode)
        new_node = node.children[remaining_key[0]]  # TODO: inline variable
        assert isinstance(new_node, BranchNode) or isinstance(new_node, ValueNode)
        node = new_node

    return tuple(path), remaining_key


def search(tree: Tree, key: Path) -> Optional[Value]:
    path, remaining_key = find_path(tree, key)
    node = path[-1]
    if isinstance(node, Tree):
        # the tree is empty
        return None
    if remaining_key:
        # the key is not in the tree
        return None
    assert isinstance(node, ValueNode)
    return node.value


def change(tree: Tree, key: Path, value: Value) -> bool:
    path, remaining_key = find_path(tree, key)
    node = path[-1]
    if isinstance(node, Tree):
        # the tree is empty
        return False
    if remaining_key:
        # the key is not in the tree
        return False
    assert isinstance(node, ValueNode)
    node.value = value
    return True


def insert(tree: Tree, key: Path, value: Value) -> bool:
    path, remaining_key = find_path(tree, key)

    if not remaining_key:
        # the key is already in the tree
        return False

    node = path[-1]
    if isinstance(node, Tree):
        # the tree is empty
        value_node: ValueNode = ValueNode(prefix=key, value=value)
        node.child = value_node
        return True
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

    parent = path[-2]
    assert isinstance(parent, BranchNode) or isinstance(parent, Tree)

    if isinstance(parent, Tree):
        parent.child = new_branch_node
    else:
        parent.children[new_branch_node.prefix[0]] = new_branch_node

    return True


def delete(tree: Tree, key: Path) -> bool:
    path, remaining_key = find_path(tree, key)

    if remaining_key:
        # the key is not in the tree
        return False

    node = path[-1]
    if isinstance(node, Tree):
        # the tree is empty
        return False

    assert isinstance(node, ValueNode)

    if len(path) == 2:
        # the tree has a single element
        tree.child = None
        return True

    parent = path[-2]
    assert isinstance(parent, BranchNode)

    brother = get_brother(node, parent)
    assert isinstance(brother, BranchNode) or isinstance(brother, ValueNode)
    brother.prefix = parent.prefix + brother.prefix

    grand_parent = path[-3]
    assert isinstance(grand_parent, BranchNode) or isinstance(grand_parent, Tree)
    if isinstance(grand_parent, Tree):
        grand_parent.child = brother
    else:
        grand_parent.children[brother.prefix[0]] = brother

    return True


def generate_digest_tree(
    node: Tree, nodes: tuple[ValueNode | BranchNode | Tree | DigestNode, ...]
) -> Tree:
    def generate_digest_tree_inner(
        node: ValueNode | BranchNode | DigestNode,
        nodes: tuple[ValueNode | BranchNode | Tree | DigestNode, ...],
    ) -> ValueNode | BranchNode | DigestNode:
        def copy_digest_node(node: DigestNode) -> DigestNode:
            return DigestNode(digest=node.digest)

        def copy_value_node(node: ValueNode) -> ValueNode:
            return ValueNode(prefix=node.prefix, value=node.value)

        def copy_branch_node(node: BranchNode) -> BranchNode:
            children = {}
            for direction, child in node.children.items():
                child_node = generate_digest_tree_inner(child, nodes)
                children[direction] = child_node
            return BranchNode(prefix=node.prefix, children=children)

        if node not in nodes:
            return DigestNode(digest=compute_hash(node))
        if isinstance(node, ValueNode):
            return copy_value_node(node)
        if isinstance(node, BranchNode):
            return copy_branch_node(node)
        if isinstance(node, DigestNode):
            return copy_digest_node(node)

    if node.child is None:
        return Tree(child=None)
    return Tree(child=generate_digest_tree_inner(node.child, nodes))


def verify_proof(
    root_digest: bytes,
    key: Path,
    value: Optional[Value],
    proof: Tree,
) -> bool:
    if compute_hash(proof) != root_digest:
        return False
    return search(proof, key) == value


def to_json(tree: Tree) -> Any:
    def to_json_digest_node(node: DigestNode) -> Any:
        return {"type": "digest", "digest": node.digest.hex()}

    def to_json_value_node(node: ValueNode) -> Any:
        return {"type": "value", "prefix": node.prefix, "value": node.value.hex()}

    def to_json_branch_node(node: BranchNode) -> Any:
        children = []
        for direction, child in node.children.items():
            children.append({"direction": direction, "child": to_json_inner(child)})
        return {"type": "branch", "prefix": node.prefix, "children": children}

    def to_json_inner(node: ValueNode | BranchNode | DigestNode) -> Any:
        if isinstance(node, DigestNode):
            return to_json_digest_node(node)
        if isinstance(node, ValueNode):
            return to_json_value_node(node)
        if isinstance(node, BranchNode):
            return to_json_branch_node(node)

    if tree.child is None:
        return {}
    return to_json_inner(tree.child)


def generate_membership_proof(tree: Tree, key: Path) -> Tuple[Tree, Optional[Value]]:
    path, remaining_key = find_path(tree, key)
    digest_tree = generate_digest_tree(tree, path)
    assert isinstance(digest_tree, Tree)
    return digest_tree, search(tree, key)


def generate_insert_proof(tree: Tree, key: Path) -> Tree:
    path, remaining_key = find_path(tree, key)

    # TODO
    if len(path) > 2:
        if remaining_key != ():
            if isinstance(path[-1], BranchNode):
                path = path + (path[-1].children[remaining_key[0]],)

    digest_tree = generate_digest_tree(tree, path)
    assert isinstance(digest_tree, Tree)
    return digest_tree


def generate_delete_proof(tree: Tree, key: Path) -> Tree:
    path, remaining_key = find_path(tree, key)

    if len(path) > 2:
        assert not isinstance(path[-1], Tree)
        assert isinstance(path[-2], BranchNode)
        path = path + (get_brother(path[-1], path[-2]),)

    digest_tree = generate_digest_tree(tree, path)
    assert isinstance(digest_tree, Tree)
    return digest_tree


def from_json(data: Any) -> Tree:
    def from_json_digest_node(data: Any) -> DigestNode:
        return DigestNode(digest=unhexlify(data["digest"]))

    def from_json_value_node(data: Any) -> ValueNode:
        return ValueNode(prefix=tuple(data["prefix"]), value=unhexlify(data["value"]))

    def from_json_branch_node(data: Any) -> BranchNode:
        children = {}
        for child in data["children"]:
            children[child["direction"]] = from_json_inner(child["child"])
        return BranchNode(prefix=tuple(data["prefix"]), children=children)

    def from_json_inner(data: Any) -> ValueNode | BranchNode | DigestNode:
        if data["type"] == "digest":
            return from_json_digest_node(data)
        if data["type"] == "value":
            return from_json_value_node(data)
        if data["type"] == "branch":
            return from_json_branch_node(data)
        raise ValueError(f"Unknown node type: {data['type']}")

    if data == {}:
        return Tree(child=None)
    return Tree(child=from_json_inner(data))


def draw(tree: Tree):
    base_indent = "  "

    def draw_inner(node: ValueNode | BranchNode | Tree | DigestNode, depth: int):
        if isinstance(node, ValueNode):
            print(f"{base_indent * depth}ValueNode({node.prefix}, {node.value})")
        if isinstance(node, BranchNode):
            print(f"{base_indent * depth}BranchNode({node.prefix})")
            for child in node.children.values():
                draw_inner(child, depth + 1)
        if isinstance(node, DigestNode):
            print(f"{base_indent * depth}DigestNode({node.digest})")
        if isinstance(node, Tree):
            print(f"{base_indent * depth}RootNode")
            if node.child is not None:
                draw_inner(node.child, depth + 1)

    draw_inner(tree, 0)
