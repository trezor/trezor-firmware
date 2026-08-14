from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardReconcile, WardReconcileAck


async def reconcile(msg: WardReconcile) -> WardReconcileAck:
    """Bind the host's root to the attested mac, and adopt it.

    This is where a device learns a tree it did not build. The host supplies the root; the
    device recomputes the mac over it at the attested counter and requires a match. Since
    K_mac never leaves the device, the host cannot produce a mac for a tree of its
    choosing, so the only root that passes is the one the attested mac was made for.
    """
    from trezor.messages import WardReconcileAck
    from trezor.wire import DataError

    from . import round as sync_round
    from .attest import root_mac, root_or_empty
    from .common import require_initialized
    from .keys import derive_k_mac, derive_ward_id
    from .root import get_counter, get_root, set_root

    require_initialized()

    ctx = sync_round.get()
    if ctx is None or ctx[0] != sync_round._ATTESTED:
        raise DataError("no attested sync round to reconcile")
    _state, _nonce, counter, mac, timestamp = ctx

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
    # A strictly greater counter is adopted, and that is now safe: writes advance the
    # counter too, so a device with unpublished writes is AHEAD of the WM and its
    # attestation is refused by the floor check rather than superseding them. The device
    # is then unable to sync until the host publishes the (counter, mac) it was handed --
    # fail-closed and recoverable, rather than a silent loss.
    #
    # A LOWER counter is adopted here without further ceremony, and that is not a hole: the
    # only way one reaches an attested round is through WardRecoverCounter, which refuses
    # anything that is not going backwards and holds for confirmation first. Re-asking here
    # would be asking about a decision already made.
    # This is also what makes BATCHING WM confirmations free today, which is worth stating
    # because it looks like missing work: a write commits its root with no WM involvement at
    # all, and any counter above the stored one is adopted here, so ten writes followed by one
    # sync round is already the supported shape. Batching only becomes real work if writes ever
    # commit solely on WM confirmation -- then each needs its own round, and amortising them is
    # part of that change rather than a prerequisite for it. See `storage/ward.py`.
    stored_counter = await get_counter()
    if counter == stored_counter:
        current = await get_root()
        # Compared in preimage form: an empty tree is stored as EMPTY_ROOT but arrives on
        # the wire as an absent field, and the two must still recognise each other.
        if current is not None and current != root_or_empty(root):
            raise DataError("attested counter matches but the root differs")

    await set_root(root, counter, timestamp)
    sync_round.clear()

    return WardReconcileAck(counter=counter, new_root=root)
