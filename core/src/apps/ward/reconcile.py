from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDReconcile, WARDReconcileAck


async def reconcile(msg: WARDReconcile) -> WARDReconcileAck:
    """Bind the host's root to the attested mac, and adopt it.

    This is where a device learns a tree it did not build. The host supplies the root; the
    device recomputes the mac over it at the attested counter and requires a match. Since
    K_mac never leaves the device, the host cannot produce a mac for a tree of its
    choosing, so the only root that passes is the one the attested mac was made for.
    """
    from trezor.messages import WARDReconcileAck
    from trezor.wire import DataError

    from . import round as sync_round
    from .attest import root_mac
    from .common import require_initialized
    from .keys import derive_k_mac, derive_ward_id
    from .root import get_counter, get_root, set_root

    require_initialized()

    ctx = sync_round.get()
    if ctx is None or ctx[0] != sync_round._ATTESTED:
        raise DataError("no attested sync round to reconcile")
    _state, _nonce, counter, mac = ctx

    root = msg.root or None
    if root is not None and len(root) != 32:
        raise DataError("root must be 32 bytes")

    expected = root_mac(await derive_k_mac(), await derive_ward_id(), counter, root)
    if expected != mac:
        raise DataError("root does not match the attested mac")

    # One counter names one state. If the WM attests the counter this device already
    # holds, the state it names must be the state this device already has -- otherwise one
    # of the two is wrong and adopting either silently discards the other.
    #
    # FIXME(ward): a STRICTLY GREATER counter is adopted, which discards local writes that
    # have not reached the WM. That window exists because writes do not yet advance the
    # counter -- they are purely local, invisible to the WM. It closes when writes go
    # through the WM and get their own attestation.
    stored_counter = await get_counter()
    if counter == stored_counter:
        current = await get_root()
        if current is not None and current != root:
            raise DataError("attested counter matches but the root differs")

    await set_root(root, counter)
    sync_round.clear()

    return WARDReconcileAck(counter=counter, new_root=root)
