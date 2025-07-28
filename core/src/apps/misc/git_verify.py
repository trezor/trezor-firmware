from typing import TYPE_CHECKING
from ubinascii import unhexlify

from trezor.wire.errors import DataError

if TYPE_CHECKING:
    from trezor.messages import GitVerify, Success


def git_hash(obj_type: str, obj: bytes) -> bytes:
    from trezor.crypto.hashlib import sha256

    h = sha256(f"{obj_type} {len(obj)}\x00")
    h.update(obj)
    return h.digest()


def verify_blob(msg: GitVerify, commit_hash: bytes) -> bytes:
    if msg.commit is None:
        raise DataError("Unset git commit")
    if msg.blob is None:
        raise DataError("Unset git blob")

    if git_hash("commit", msg.commit) != commit_hash:
        raise DataError("Invalid git commit")

    # expected hash of root tree
    expected_hash = unhexlify(msg.commit.split(None, 2)[1])

    if len(msg.trees) != len(msg.path):
        raise DataError("Path doesn't match trees")

    for tree, child_name in zip(msg.trees, msg.path):
        if git_hash("tree", tree) != expected_hash:
            raise DataError("Invalid git tree")
        tree_view = memoryview(tree)

        children = {}
        while tree_view:
            offset = next(i for i, v in enumerate(tree_view) if v == 0)
            line = bytes(tree_view[:offset]).decode()
            _mode, name = line.split(" ", 1)
            tree_view = tree_view[offset + 1 :]  # skip 0
            tree_hash, tree_view = tree_view[:32], tree_view[32:]
            children[name] = tree_hash

        expected_hash = children[child_name]

    if git_hash("blob", msg.blob) != expected_hash:
        raise DataError("Invalid git blob")

    return msg.blob


async def git_verify(msg: GitVerify) -> Success:
    from storage import device
    from trezor.messages import Success
    from trezor.ui.layouts import show_success

    commit_hash = device.get_git_commit_hash()
    if commit_hash is None:
        raise DataError("Unset git commit hash")

    blob = verify_blob(msg, commit_hash)
    await show_success(
        br_name="git_commit_verify", content=blob.decode(), subheader="/".join(msg.path)
    )
    return Success()
