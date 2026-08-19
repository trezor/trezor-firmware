from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardQueueGetAck, WardQueueGetEntry


async def queue_get_entry(msg: WardQueueGetEntry) -> WardQueueGetAck:
    """WardQueueGetEntry handler: show what the DEVICE holds, with no host involved.

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

    THE ACK CARRIES NO VALUE. What was found goes to the screen and stays there; the host gets
    flags. Returning the value would hand back the one thing this store exists to serve WITHOUT
    a host, and for a queued change the host has never seen it at all. The flags are what a host
    can act on: prompt the user to connect, warn that a change is still outstanding, or note that
    what was shown is known to be behind.
    """
    from trezor.messages import WardQueueGetAck
    from trezor.ui.layouts import confirm_properties

    from . import offline_store
    from .common import display_bytes, require_key
    from .keys import ENTRY_TYPE_ADDRESS, entry_key_for

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
        # A change the user confirmed that no host has taken yet. It is what this device
        # believes, not what WARD holds.
        title = "Pending change"
        props.append(("Value", display_bytes(entry.value), True))
        props.append(
            ("Warning", "Not published yet. Connect to apply this change.", False)
        )
        ack = WardQueueGetAck(
            entry_key=entry_key,
            pending=True,
            stale=entry.stale,
            counter=entry.counter,
        )
    else:
        title = "Offline copy"
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
        ack = WardQueueGetAck(
            entry_key=entry_key,
            stale=entry.stale,
            counter=entry.counter,
        )

    await confirm_properties("ward_queue_get_entry", title, props)

    return ack
