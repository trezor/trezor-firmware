from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardVerifyChain, WardVerifyChainAck


async def verify_chain(msg: WardVerifyChain) -> WardVerifyChainAck:
    """Adopt the attested head by proving it DESCENDS from the head this device holds.

    Runs after WardIngestAttestation, in place of WardReconcile. Where reconcile takes the
    new head on the WM's word plus a mac, this additionally establishes that every step
    between here and there was authorised by a device of this wallet and that none was
    skipped -- which is what a device needs after another device wrote while it was away.

    GAP(ward): multi-device is exercised only through the host ORACLE -- `tests/ward_trie.py`
    serves both the links and the proofs, and no test runs two real devices against one trie.
    Evolu's own history makes a real one possible, because replaying it is exactly how a
    second device catches up: rebuild live state from `evolu_history` to serve proofs, then
    feed the transitions here as WardChainLink to prove descent. Both halves come from one
    source rather than two that can disagree -- a history row carries the leaf and the counter,
    a link carries the roots and the auth_commit the device issued alongside it. The test wants
    two emulators on one seed: A writes, B replays and verifies, and B's derived head must
    equal A's.

    The two guarantees are complementary and both are required: the chain gives DESCENT,
    the attestation gives CURRENCY, and they are joined by demanding the chain end exactly
    at the attested counter with a root that reproduces the attested mac. Either alone is
    forgeable in a way the pair is not -- a chain to some genuine older head, or an
    attestation of a head reached by a fork.
    """
    from trezor.messages import WardVerifyChainAck
    from trezor.wire import DataError

    from . import round as sync_round
    from .attest import root_mac
    from .cas import verify_chain_step
    from .common import require_initialized
    from .keys import derive_k_auth, derive_k_mac, derive_ward_id
    from .root import get_counter, get_root, set_root

    require_initialized()

    ctx = sync_round.get()
    if ctx is None or ctx[0] != sync_round._ATTESTED:
        raise DataError("no attested sync round to verify against")
    _state, _nonce, counter, mac = ctx

    ward_id = await derive_ward_id()
    k_auth = await derive_k_auth()

    # The baseline is the device's OWN head, not anything the host names. A host-chosen
    # starting point would let the walk begin at a state this device never reached.
    running_counter = await get_counter()
    running_root = await get_root()

    for link in msg.links:
        running_counter, running_root = verify_chain_step(
            k_auth,
            ward_id,
            running_counter,
            running_root,
            (
                link.from_counter,
                link.from_root or None,
                link.to_counter,
                link.to_root or None,
                link.auth_commit,
            ),
        )

    if running_counter != counter:
        raise DataError("chain does not end at the attested counter")

    # ...and the state it ends in must be the state that was attested. Without this the
    # chain could authorise a walk to a head the WM never vouched for.
    if root_mac(await derive_k_mac(), ward_id, counter, running_root) != mac:
        raise DataError("chain end does not match the attested mac")

    await set_root(running_root, counter)
    sync_round.clear()

    return WardVerifyChainAck(counter=counter, new_root=running_root)
