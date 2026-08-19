from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardQueueSetAck, WardQueueSetEntry


async def queue_set_entry(msg: WardQueueSetEntry) -> WardQueueSetAck:
    """WardQueueSetEntry handler: hold a write on the device until a synced host can take it.

    ASKED FOR BY NAME, not fallen back to. `WardSetEntry` used to queue silently when the
    session was unsynced, so one request meant two things depending on state the host cannot
    see. A host that wants to queue now says so, and gets an ack type that can only mean that.

    WHY THIS CANNOT PRODUCE A LEAF. With no synced host the device cannot pull, so it cannot
    prove current state, cannot derive a root and cannot stamp a counter. What it stores is an
    INTENT -- a value for a path -- and the intent is sealed and published later by
    `flush_queue`, re-derived against whatever the tree has become by then.

    The old value shown is the device's own copy if it has one. That is weaker than the online
    screen, which shows what the host proved, so it is labelled as a local copy rather than
    presented as the current value. Showing nothing would be worse: an overwrite the user cannot
    see is the failure the online path already designs against, and being offline does not make
    it less true.

    THE SCREEN HAS TO SAY QUEUED rather than done. A confirmation that reads as "applied" when
    nothing has been applied is the failure `storage/ward.py` warns about: the user holds, the
    change sits in flash, and they have no reason to think anything is outstanding.
    """
    from trezor.messages import WardQueueSetAck
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from . import offline_store
    from .common import display_bytes, require_key
    from .keys import ENTRY_TYPE_ADDRESS, entry_key_for

    app_id, identifier = require_key(msg.app_id, msg.identifier)

    # Empty is a legitimate value; absent is not. Writing "nothing specified" as if it were an
    # empty value would silently blank an entry, so require the field -- exactly as the online
    # write does, because queueing must not be the lenient door into the same store.
    value = msg.value
    if value is None:
        raise DataError("value is required")

    key_type = ENTRY_TYPE_ADDRESS
    entry_key = await entry_key_for(app_id, identifier, key_type)

    status, existing = await offline_store.get(entry_key)

    props = [
        ("Domain", app_id, False),
        ("Key", display_bytes(identifier), True),
    ]
    if status == offline_store.VALID and existing is not None:
        title = "Queue update"
        props.append(("Replaces (local copy)", display_bytes(existing.value), True))
    else:
        title = "Queue new entry"
    props.append(("New value", display_bytes(value), True))
    props.append(
        (
            "Warning",
            "Not applied yet. Held on this device until you connect.",
            False,
        )
    )

    await confirm_properties("ward_queue_entry", title, props)

    # Stored only after confirmation, and with counter 0 -- "no counter assigned". The counter is
    # stamped by `flush_queue` when the change is finally derived against a real root.
    await offline_store.put(
        entry_key,
        key_type,
        app_id,
        identifier,
        0,
        value,
        0,
        True,
    )

    # entry_key and nothing else. There is no counter, no mac and no leaf because none of them
    # exists yet, and the ack type says so without needing a flag. The path is still worth
    # returning: the host's store is organised by it and it has no other way to learn it.
    return WardQueueSetAck(entry_key=entry_key)
