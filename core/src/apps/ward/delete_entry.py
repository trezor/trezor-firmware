from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardDeleteEntry, WardLeafAck


async def delete_entry(msg: WardDeleteEntry) -> WardLeafAck:
    """WardDeleteEntry handler: confirm removing a host-held entry.

    The device pulls the entry first so the screen can name what is being removed --
    confirming a deletion by key alone tells the user nothing about what they are
    losing. Held-to-confirm, because it is destructive and unlike a write it cannot be
    undone by repeating it with the old value (the host is the only place that value
    still exists).

    Returns a leaf with BOTH PARTS EMPTY. That is the wire's way of saying "deleted",
    and the host removes the record entirely -- WARD does a full delete, so a later
    non-membership proof for this path must succeed. Note the reference keeps the
    identity part alive on delete, leaving a self-describing tombstone; we do not, since
    a tombstone that survives is a record of which entries once existed.

    THE HOST'S DELETE IS EVOLU'S, NOT OURS. Rebuilding the trie on the host by sweeping to
    genesis needs every historical change, deletions included -- and Evolu already keeps them.
    `evolu_history` is an append-only (table, id, column, timestamp, value) log, written on
    every message application, so a freshly synced replica reconstructs the whole history; and
    Evolu has NO hard delete at all, since `isDeleted` is a system column and removing a row
    means setting it. See docs/core/misc/ward-trie.md.

    So there is nothing for WARD to decide here and nothing to add: the trie is built over
    rows with isDeleted = false, which is the same filter every other Evolu consumer applies,
    and the sweep reads the history that exists regardless. The leaf below, with both parts
    empty, is the SIGNAL to set that flag -- not a second source of truth for tree membership.
    Keying membership off "empty content part" as well would be two rules that can disagree,
    and one of them would be WARD-specific.

    The privacy of a full delete was never ours to trade: the store retains the history
    whichever way we encode it, so "no tombstone" only ever hid past entries from a party
    seeing current state alone. Reclaiming it would have to happen at the store layer.

    DECIDED, NOT YET BUILT: a delete's payload becomes a SEALED TOMBSTONE, and a queued
    intent additionally carries a MAC over (entry_key, op, counter) under K_auth. Both,
    because each closes an attack the other cannot -- and the pair only matters once queued
    intents are uploaded for another device to integrate.

      The tombstone stops a FORGED delete. Today `EMPTY_PART` is plaintext with an empty
      body in both parts, so any host can construct a delete leaf for any entry_key. A
      sealed payload can only come from a holder of K_data.

      The intent MAC stops a REPLAYED GENUINE WRITE presented as a queued intent at a path
      that has since been deleted -- re-adding data the user deleted. The tombstone cannot
      stop that: the leaf is authentic, and a deleted path has NO current leaf, so C_leaf
      has nothing to be compared against. Only a counter inside an authenticated intent
      bounds it.

      PARTLY BUILT NOW. `cas.intent_mac` authenticates a queued intent, and `queue_set_entry`
      verifies one on the way back in -- so a host can hold a queue backup it cannot forge.
      The COUNTER is not in that preimage, though, so the replay above is still open: a
      restore carries no counter, and adding one back is a wire change. The tombstone half
      remains unbuilt, and queued deletes remain impossible.

    Both are the same lesson as the sibling-kind fix that this file used to carry: anything
    inferred from an absent or empty field is host-controlled. A cleartext op discriminator
    would be too, which is why the op goes inside the MAC.

    IDEMPOTENT ON A PROVED ABSENCE. Deleting a path that already holds nothing succeeds,
    changing nothing: same empty leaf, same counter, no authorised transition, and no
    screen. It is not a favour to sloppy hosts -- the absence has already been PROVED by
    the time this decides anything, because `pull_leaf` demands a non-membership witness
    against the trusted root before it will report nothing. So the device is not taking
    "I do not have it" on the host's word; it has checked, which makes this strictly more
    verified than the refusal it replaces.

    There is deliberately no confirmation for the no-op. A hold-to-confirm that always
    means "nothing happened" is a screen that gets approved without being read, which
    costs real safety on the paths where holding matters.

    REQUIRES A CONNECTION, and offline it refuses. A queued delete cannot be made safe with
    what exists today: `EMPTY_PART` is plaintext with an empty body in both parts, so any host
    can construct a delete leaf for any entry_key, and uploading queued deletes would hand a
    host the power to delete anything. Closing that needs the sealed tombstone AND the intent
    MAC described above -- both, since each stops an attack the other cannot. Until they exist,
    refusing is the only honest answer; a write can wait in a queue, a delete cannot.

    IT NEVER TOUCHES THE DEVICE'S OFFLINE COPY, and that is deliberate rather than an
    oversight. This removes the entry from WARD; `WardEraseCachedEntry` removes the local copy.
    They are different questions and one confirmation cannot honestly stand for both -- the
    user holding to delete an entry has not been asked whether they also want the copy they
    chose to keep on this device destroyed. The consequence is accepted: an entry deleted here
    still reads offline, marked as a local copy, until the user removes it deliberately. That
    is the recoverable direction, and it follows the same rule as everywhere else in this
    subsystem -- nothing erases a record except the user saying so.

    A host reporting an entry ABSENT is likewise not permission to erase the local copy. It is
    the host's claim about the host's state, and the local copy is not the host's to discard.

    WHAT THIS DOES NOT FIX. If a delete succeeds and its response is lost, the host still
    holds the row and the pre-delete root, so a retry serves that row with a proof against
    a root the device has already moved past -- refused, correctly, as a stale current
    state. Idempotence covers the retry AFTER the host has applied the delete, which is the
    natural pattern once a host derives the post-delete root itself (it can: it holds the
    whole tree). Closing the un-applied case needs the host to be able to ASK for the
    device's head, which no message currently offers.
    """
    from trezor.messages import WardLeafAck
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from .attest import root_mac
    from .cas import auth_commit, sig_commit
    from .common import (
        WARNING_UNVERIFIED,
        display_bytes,
        online,
        pull_leaf,
        require_key,
    )
    from .keys import (
        ENTRY_TYPE_ADDRESS,
        derive_k_auth,
        derive_k_mac,
        derive_k_sig,
        derive_ward_id,
        entry_key_for,
    )
    from .leaf import EMPTY_PART, make_leaf_content, make_leaf_identity
    from .root import get_counter, get_root
    from .trie import compute_new_root

    app_id, identifier = require_key(msg.app_id, msg.identifier)

    if not await online():
        raise DataError("WARD: connect to delete an entry")

    key_type = ENTRY_TYPE_ADDRESS
    entry_key = await entry_key_for(app_id, identifier, key_type)
    current, old_leaf, material = await pull_leaf(entry_key, key_type)
    if current is None:
        # Already gone, and provably so. Report the state rather than changing it: the
        # counter does not move, and no auth_commit is issued because no transition
        # happened -- an authorisation for (n, R) -> (n, R) would be a link that authorises
        # nothing and would pollute the chain any other device has to walk.
        #
        # The mac IS returned, over the device's current head, and that is the useful part:
        # a host that believes it is a counter behind learns from this that its earlier
        # delete did land. The mac grants nothing new -- any write hands one out, and the
        # counter floor bounds what a replayed one can do.
        counter = await get_counter()
        return WardLeafAck(
            entry_key=entry_key,
            identity=make_leaf_identity(key_type, EMPTY_PART),
            content=make_leaf_content(EMPTY_PART),
            counter=counter,
            mac=root_mac(
                await derive_k_mac(), await derive_ward_id(), counter, await get_root()
            ),
        )

    props = [
        ("Domain", app_id, False),
        ("Key", display_bytes(identifier), True),
        ("Deleting value", display_bytes(current), True),
        WARNING_UNVERIFIED,
    ]

    await confirm_properties("ward_delete_entry", "Delete entry", props, hold=True)

    # Derive the root the deletion leaves behind. The sibling decomposition matters here:
    # The sibling of the removed leaf promotes unchanged -- a node's hash does not depend on
    # its depth, so re-parenting costs nothing. This used to need a witness for the sibling's
    # KIND; see `trie.compute_new_root`.
    proof, _witness_key, _witness_commit = material
    from_root = await get_root()
    counter = await get_counter() + 1
    new_root = compute_new_root(
        entry_key,
        old_leaf,
        None,
        proof,
        from_root,
    )
    # NOT COMMITTED HERE. The device hands back the root it derived, its counter and the
    # authenticators; the head only moves when a WM attestation names that counter and a mac
    # the device can reproduce -- see `reconcile`. That is what makes "the head is always a
    # state the WM confirmed" an invariant, and it is what the fork check exists in spite of:
    # two devices can no longer both hold an unconfirmed counter N+1, because neither holds
    # one at all. Nothing needs storing in the meantime -- the mac is self-validating, so the
    # device can accept the root later purely because it reproduces the attested mac.

    return WardLeafAck(
        entry_key=entry_key,
        identity=make_leaf_identity(key_type, EMPTY_PART),
        content=make_leaf_content(EMPTY_PART),
        counter=counter,
        mac=root_mac(await derive_k_mac(), await derive_ward_id(), counter, new_root),
        auth_commit=auth_commit(
            await derive_k_auth(),
            await derive_ward_id(),
            counter - 1,
            from_root,
            counter,
            new_root,
        ),
        auth_sig=sig_commit(
            await derive_k_sig(),
            await derive_ward_id(),
            counter - 1,
            from_root,
            counter,
            new_root,
        ),
    )
