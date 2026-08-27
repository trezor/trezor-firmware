"""What every route into a new head has in common.

FOUR HANDLERS TOUCH THE SYNC ROUND, in two pairs, and each pair duplicated a sequence:

    ingest / recover           verify the WM's attestation against this round's nonce, then apply
                               opposite counter rules to it -- forward-only for the ordinary path,
                               backwards-only for the recovery one.

    reconcile / verify_chain    bind a root to the attested mac, settle queued writes against it,
                               persist it, and latch the session online. They differ ONLY in how
                               they establish the root: reconcile takes the host's and checks the
                               mac; verify_chain folds authorised links from the device's own head.

Factored out because the sequences are security-relevant and were drifting: the online latch was
added to `reconcile` and forgotten in `verify_chain`, and the check that a root was actually stored
had to be added to both. A third route -- a device-initiated sync over a service channel -- will
want the same tail, and copying it a third time is how the next asymmetry gets introduced.

WHAT IS DELIBERATELY NOT FACTORED. The route-specific proof stays with its handler: reconcile's
"one counter names one state" comparison and verify_chain's link fold are what distinguish the two,
and hiding either behind a shared helper would make the weaker route look like the stronger one.
The ORDER of the remaining steps is load-bearing rather than incidental, which is why `verify_head_mac`
and `adopt` are separate: reconcile has a check that must run between them.
"""

from typing import Any


async def verify_round_attestation(msg: Any) -> "tuple[int, bytes]":
    """Check a WM attestation against the OPEN round, and return its (counter, mac).

    Verifies only that some authority the device trusts said this (counter, mac) is current, and
    said it in answer to THIS round's nonce. Adopts nothing -- no root has been seen yet -- and
    applies NO counter rule, because the two callers want opposite ones: `ingest` refuses anything
    older than the stored floor, `recover` refuses anything that is not older. Putting either rule
    here would let the other route reach the wrong one.
    """
    from trezor.wire import DataError

    from . import round as sync_round
    from .attest import verify_attestation
    from .keys import derive_ward_id

    ctx = sync_round.get()
    if ctx is None:
        raise DataError("no sync round in progress")
    _state, nonce, _c, _m = ctx

    counter = msg.counter
    mac = msg.mac
    signature = msg.wm_signature
    timestamp = msg.timestamp or 0
    if counter is None or mac is None or signature is None:
        raise DataError("counter, mac and wm_signature are required")

    if not verify_attestation(
        await derive_ward_id(), nonce, counter, mac, timestamp, signature
    ):
        raise DataError("WM attestation verification failed")

    # NO TIME CHECK. The attestation still carries a timestamp and it is still covered by the
    # signature, but nothing compares it: anti-replay is the counter's job, a malicious WM simply
    # lies about the clock, and an honest one whose clock regressed without its counter regressing
    # was never an attack. Storing a time to compare against bought nothing, so the device stops
    # storing one -- see `storage.ward`. The field stays on the wire because removing it from the
    # preimage would be a version bump for no gain today.
    return counter, mac


def require_attested_round(what: str) -> "tuple[int, bytes]":
    """The (counter, mac) this round attested, or refuse.

    An adoption route may only run against a round that reached ATTESTED: the nonce alone proves
    nothing, and a verified signature that was never bound to a tree adopts nothing either.
    """
    from trezor.wire import DataError

    from . import round as sync_round

    attested = sync_round.get_attested()
    if attested is None:
        raise DataError("no attested sync round to " + what)
    return attested


async def verify_head_mac(
    counter: int, mac: bytes, root: bytes | None, subject: str = "root"
) -> None:
    """Require that this root is the one the attested mac was made for.

    K_mac never leaves the device, so a host cannot produce a mac for a tree of its choosing: the
    only root that reproduces the attested mac is the one it was computed over. That is what lets
    a device adopt a tree it did not build.

    `subject` names what failed, because the two routes arrive here having established the root
    differently and the distinction is worth keeping in the error: a host-supplied root that does
    not match is a different problem from a chain that folded to a head the WM never vouched for.
    """
    from trezor.wire import DataError

    from .attest import root_mac
    from .keys import derive_k_mac, derive_ward_id

    expected = root_mac(await derive_k_mac(), await derive_ward_id(), counter, root)
    if expected != mac:
        raise DataError(subject + " does not match the attested mac")


async def adopt(
    counter: int, root: bytes | None, landed_commits: "list | None" = None
) -> None:
    """Take the head: settle queued writes, persist it, latch online, close the round.

    THE ORDER IS THE CONTRACT, and each step's reason for being where it is:

      SETTLE FIRST. A claim names the transition it was filed for, so once the stored head is at
      or past that transition the walk that would have proved it is behind every future sync's
      baseline and no later adoption can decide it. Crash before settling and the next sync
      crosses the transition again; crash after and the claim is already resolved. The reverse
      order has no safe crash point.

      THEN PERSIST, AND CHECK THAT IT PERSISTED. `storage.ward` refuses a ninth wallet rather than
      evicting one of the eight it protects, so a full store means the verified head was NOT kept.
      Latching online after that would leave the session verifying against a root that does not
      exist, and `common.verify_leaf_against_root` reads an absent root at counter 0 as "nothing
      was ever written" and stops checking proofs at all.

      THEN LATCH. Reads may go to the host only once a WM attestation has been bound to a tree the
      device actually holds.

      THEN CLOSE THE ROUND, so one attestation can never be replayed into a second adoption.

    `landed_commits`, when given, is every transition the caller proved it crossed; a claim landed
    exactly when its own authorisation is among them. Without it, settlement falls back to the
    counter comparison -- see `offline_store.reconcile_pending`.
    """
    from trezor.wire import DataError

    from . import round as sync_round
    from .offline_store import reconcile_pending
    from .root import set_root

    await reconcile_pending(counter, landed_commits=landed_commits)

    if not await set_root(root, counter):
        raise DataError(
            "WARD: no root slot for this wallet; eight already hold one, so this one can only be used offline"
        )

    sync_round.mark_online()
    sync_round.clear()
