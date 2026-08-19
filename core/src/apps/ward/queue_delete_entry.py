from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardQueueDeleteAck, WardQueueDeleteEntry


async def queue_delete_entry(msg: WardQueueDeleteEntry) -> WardQueueDeleteAck:
    """WardQueueDeleteEntry handler: DISCARD a queued change, on confirmation.

    NOT A WARD DELETION. Nothing here touches the trie: the change being discarded was never
    published, so there is no leaf, no root and no counter involved. `WardDeleteEntry` remains
    the only way to remove an entry from WARD, and it still requires a synced session -- a
    delete cannot be queued, because `EMPTY_PART` is plaintext and a host able to hand over
    delete leaves could delete anything.

    PENDING RECORDS ONLY. A record the user PINNED for offline reading sits in the same store
    and is deliberately out of reach here: "do not publish this change" and "stop keeping this
    value on the device" are different questions, and one confirmation cannot honestly stand for
    both. `WardEraseCachedEntry` is the pinned-copy path, and it is the only place a pinned
    record can be destroyed.

    NOTHING QUEUED IS AN ANSWER, NOT A FAILURE. `missing` is reported instead of raising: a host
    reconciling its own view of the queue will legitimately ask about a path whose change has
    already been published, and a Failure would make that ordinary case look like a fault. No
    screen is shown for it either -- a hold-to-confirm that always means "nothing happened" is
    one that gets approved without being read, which costs real safety where holding matters.

    THE DEVICE DERIVES THE PATH from (app_id, identifier), as every other request does, so a
    host cannot name an arbitrary slot to discard.
    """
    from trezor.messages import WardQueueDeleteAck
    from trezor.ui.layouts import confirm_properties

    from . import offline_store
    from .common import display_bytes, require_key
    from .keys import ENTRY_TYPE_ADDRESS, entry_key_for

    app_id, identifier = require_key(msg.app_id, msg.identifier)

    key_type = ENTRY_TYPE_ADDRESS
    entry_key = await entry_key_for(app_id, identifier, key_type)

    status, entry = await offline_store.get(entry_key)

    # A record this build cannot read is reported as MISSING rather than discarded. It may be a
    # queued change written by a newer firmware, and destroying it to tidy up would lose a change
    # the user confirmed -- the one thing the erase rule forbids outright. `WardEraseCachedEntry`
    # has the deliberate, user-confirmed escape hatch for such a record.
    if status != offline_store.VALID or entry is None or not entry.pending:
        return WardQueueDeleteAck(entry_key=entry_key, missing=True)

    await confirm_properties(
        "ward_queue_delete_entry",
        "Discard queued change?",
        [
            ("Domain", app_id, False),
            ("Key", display_bytes(identifier), True),
            ("Discarding", display_bytes(entry.value), True),
            ("Warning", "This change was never published. It will be lost.", False),
        ],
        hold=True,
    )

    # After the confirmation returns, so a rejected screen leaves the record byte-for-byte as it
    # was -- ActionCancelled propagates out before any write.
    await offline_store.erase(entry_key)

    return WardQueueDeleteAck(entry_key=entry_key)
