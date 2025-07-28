from typing import TYPE_CHECKING
from ubinascii import hexlify

if TYPE_CHECKING:
    from trezor.messages import GitCommitUpdate, Success


async def git_commit_update(msg: GitCommitUpdate) -> Success:
    from storage import device
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_blob

    commit_hash = msg.commit_hash or (b"\x00" * 32)

    await confirm_blob(
        br_name="git_commit_update",
        title="Update git commit?",
        data=hexlify(commit_hash).decode(),
        info=False,
        chunkify=True,
    )

    device.set_git_commit_hash(commit_hash)
    return Success()
