from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardQueueSetAck, WardQueueSetEntry


async def queue_set_entry(msg: WardQueueSetEntry) -> WardQueueSetAck:
    """WardQueueSetEntry handler: hold a write on the device, or RESTORE one it held before.

    ASKED FOR BY NAME, not fallen back to. `WardSetEntry` used to queue silently when the
    session was unsynced, so one request meant two things depending on state the host cannot
    see. A host that wants to queue now says so, and gets an ack type that can only mean that.

    TWO SHAPES, TOLD APART BY `mac`, and the discriminator is cryptographic rather than declared:
    a fresh intent has none, a restore carries the one `queue_get_entry` produced. The restore path
    verifies BEFORE it shows anything -- a confirmation screen for bytes that failed to
    authenticate would teach the user that the screen means nothing.

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

    # A restore states its key space, because that string is inside the MAC and defaulting it here
    # would mean verifying a preimage the exporter never built.
    key_type = msg.key_type if msg.mac is not None else ENTRY_TYPE_ADDRESS
    if key_type is None:
        raise DataError("WARD: key_type is required to restore a queued change")
    entry_key = await entry_key_for(app_id, identifier, key_type)

    if msg.mac is not None:
        return await _restore(
            app_id, identifier, entry_key, key_type, value, msg.counter or 0, msg.mac
        )

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


async def _restore(
    app_id: str,
    identifier: bytes,
    entry_key: bytes,
    key_type: str,
    value: bytes,
    counter: int,
    mac: bytes,
) -> "WardQueueSetAck":
    """Put back a queued change this wallet authenticated on the way out.

    WHY A MAC AND NOT TRUST. The blob was held by the HOST, which is free to change any byte of it.
    Every field the device would write back is inside the MAC -- see `cas.intent_preimage` -- so a
    substituted value, a moved path or an edited counter all fail here rather than becoming a
    queued change the user never confirmed. Note the entry_key is DERIVED from (app_id, identifier)
    as always and then MAC-checked, so a host cannot aim a restore at a path of its choosing even
    with an otherwise valid blob.

    VERIFY, THEN SHOW, THEN WRITE. Failing before the screen is the point: a confirmation for
    material that did not authenticate trains the user to approve one, and the whole value of the
    hold is that it is rare and meaningful.

    THE USER STILL CONFIRMS. They confirmed this change once, on some device, at some time -- but
    what arrives here is bytes from a host, and the hold is what makes "this came back" visible.
    Silently re-queueing on a MAC alone would make a restore indistinguishable from nothing
    happening.

    GAP(ward): NO REPLAY BOUND. A MAC proves this wallet queued these bytes, never that they should
    be queued NOW. So a host may re-offer a change the user discarded, or one already published,
    and this accepts it. Closing that needs the counter compared against the device's trusted head
    (already published => refuse) and the slot required to be free (a queued change already here =>
    refuse); `counter` is carried and MAC'd precisely so that becomes a handler change rather than
    a wire change.
    """
    from trezor.messages import WardQueueSetAck
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from . import offline_store
    from .cas import OP_SET, verify_intent_mac
    from .common import display_bytes
    from .keys import derive_k_auth, derive_ward_id

    if not verify_intent_mac(
        await derive_k_auth(),
        await derive_ward_id(),
        entry_key,
        OP_SET,
        counter,
        key_type,
        app_id,
        identifier,
        value,
        mac,
    ):
        raise DataError("WARD: this queued change was not authenticated by this wallet")

    await confirm_properties(
        "ward_queue_restore_entry",
        "Restore queued change?",
        [
            ("Domain", app_id, False),
            ("Key", display_bytes(identifier), True),
            ("Value", display_bytes(value), True),
            (
                "Warning",
                "From a backup. Still not applied -- held until you connect.",
                False,
            ),
        ],
    )

    # Restored PENDING, at the counter it was exported with. Zero means "no counter assigned", so a
    # change that had never been handed to a host comes back in exactly that state and `flush_queue`
    # will offer it again.
    await offline_store.put(
        entry_key,
        key_type,
        app_id,
        identifier,
        0,
        value,
        counter,
        True,
    )

    return WardQueueSetAck(entry_key=entry_key)
