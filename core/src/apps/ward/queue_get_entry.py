from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardQueueGetAck, WardQueueGetEntry


async def queue_get_entry(msg: WardQueueGetEntry) -> WardQueueGetAck:
    """WardQueueGetEntry handler: EXPORT what the DEVICE holds, so the host can back it up.

    NO PULL HAPPENS HERE, and that is the point rather than a limitation. A host that does not
    speak WARD cannot answer `WardEntryRequest`, and a host that does but has not synced has not
    shown the device anything current -- so this reads the device's own store and emits no
    request at all. Because the source is chosen by the MESSAGE, not by hidden session state, a
    hostile host can no longer force a local copy onto the screen by failing a pull: that path
    now errors instead of falling back (see `get_entry`).

    THREE THINGS THE SCREEN MUST NOT CONFLATE: a copy the user pinned, a change the user made
    that no host has taken yet, and nothing at all. Each gets its own title, because a pending
    change shown in the wording of a stored value would make the user's earlier confirmation
    retroactively untrue.

    UNREADABLE IS NOT MISSING. A record this build cannot decode -- a newer format, damaged
    framing -- is named as such, on screen and in the ack. Reporting "nothing here" would invite
    writing over it while telling the user it was never there.

    BACKUP IS WHY THIS EXISTS. A queued change lives in this device's flash and nowhere else, so
    losing the device loses a change the user confirmed. The ack therefore carries the RECORD --
    key_type, app_id, identifier, value, counter -- and, for a pending record, a MAC over all of
    it under K_auth. `queue_set_entry` accepts those bytes back only if the MAC verifies, so a
    backup is something a host can hold without being able to invent one.

    THE BLOB IS PLAINTEXT, and that is a deliberate exception rather than an oversight. The host's
    leaf store contains no identifiers -- that is what the keyed path buys -- but a queue backup
    contains identifier and value, including for a change queued by an on-device app that the host
    never saw. The trade is that a backup is inspectable and restorable by a host holding no device
    key at all.

    A PINNED COPY GETS NO MAC. It is not an intent: nothing queued it, and there is nothing to
    re-queue. Returning a MAC for one would invite a restore that means nothing, so the fields come
    back for the host's records and the MAC does not.

    THE USER CONFIRMS THE EXPORT, because it is the only notice they get that a value the device
    was holding for itself is leaving.
    """
    from trezor.messages import WardQueueGetAck
    from trezor.ui.layouts import confirm_properties

    from . import offline_store
    from .cas import OP_SET, intent_mac
    from .common import display_bytes, require_key
    from .keys import ENTRY_TYPE_ADDRESS, derive_k_auth, derive_ward_id, entry_key_for

    app_id, identifier = require_key(msg.app_id, msg.identifier)

    key_type = ENTRY_TYPE_ADDRESS
    entry_key = await entry_key_for(app_id, identifier, key_type)

    status, entry = await offline_store.get(entry_key)

    props = [
        ("Domain", app_id, False),
        ("Key", display_bytes(identifier), True),
    ]

    if status == offline_store.CORRUPT or (status == offline_store.VALID and entry is None):
        title = "Cannot be read"
        props.append(
            ("Result", "Something is stored here that this firmware cannot read.", False)
        )
        ack = WardQueueGetAck(entry_key=entry_key, unreadable=True)
    elif status == offline_store.MISS or entry is None:
        title = "Not kept offline"
        props.append(("Result", "No offline copy. Connect to read this entry.", False))
        ack = WardQueueGetAck(entry_key=entry_key, missing=True)
    elif entry.pending:
        # A change the user confirmed that no host has taken yet. It is what this device believes,
        # not what WARD holds -- and the one kind of record worth backing up, since it exists
        # nowhere else.
        title = "Back up queued change?"
        props.append(("Value", display_bytes(entry.value), True))
        props.append(
            (
                "Warning",
                "Not published yet. The value is sent to the host so it can be restored.",
                False,
            )
        )
        ack = WardQueueGetAck(
            entry_key=entry_key,
            pending=True,
            stale=entry.stale,
            counter=entry.counter,
            key_type=entry.key_type,
            app_id=entry.app_id,
            identifier=entry.identifier,
            value=entry.value,
            mac=intent_mac(
                await derive_k_auth(),
                await derive_ward_id(),
                entry_key,
                OP_SET,
                entry.counter,
                entry.key_type,
                entry.app_id,
                entry.identifier,
                entry.value,
            ),
        )
    else:
        title = "Send offline copy?"
        props.append(("Value", display_bytes(entry.value), True))
        props.append(("Kept at", "counter " + str(entry.counter), False))
        props.append(
            (
                "Warning",
                (
                    "May be out of date; the entry has changed since."
                    if entry.stale
                    else "Local copy, not checked against the host."
                ),
                False,
            )
        )
        # No MAC: this is a copy of something WARD already holds, not a change waiting to be
        # published, so there is no intent for a restore to re-queue.
        ack = WardQueueGetAck(
            entry_key=entry_key,
            stale=entry.stale,
            counter=entry.counter,
            key_type=entry.key_type,
            app_id=entry.app_id,
            identifier=entry.identifier,
            value=entry.value,
        )

    await confirm_properties("ward_queue_get_entry", title, props)

    return ack
