from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import Success, WARDDebugSetRoot


async def debug_set_root(msg: WARDDebugSetRoot) -> Success:
    """Seed the root the device verifies proofs against. DEBUG BUILDS ONLY.

    Registered behind `if __debug__`, so a release build cannot reach this and therefore
    holds no root and verifies nothing -- which its screens say. That is the honest
    state until roots become attested; a device that accepted a root from whoever asked
    would be verifying proofs against a number its adversary chose, which is worse than
    not verifying at all, because it looks like verification.

    No confirmation screen: it is unreachable outside a debug build, and adding one would
    only make tests slower.
    """
    from trezor.messages import Success

    from .root import set_root

    root = msg.root or None
    if root is not None and len(root) != 32:
        from trezor.wire import DataError

        raise DataError("root must be 32 bytes")

    set_root(root)
    return Success(message="WARD root set")
