from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardQueueSetAck, WardQueueSetEntry


async def queue_set_entry(msg: WardQueueSetEntry) -> WardQueueSetAck:
    """WardQueueSetEntry handler: hold a write on the device, or RESTORE one it held before.

    Stores an INTENT, not a leaf: with no synced host the device cannot prove state, so
    `flush_queue` re-derives it later. A request with `mac` is a restore of a `queue_get_entry`
    backup and is verified before anything is shown. The screen names what it replaces and says
    QUEUED, not done. `compact` stores a hash of the identity instead of the identity.
    """
    from trezor.messages import WardQueueSetAck
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from . import offline_store
    from .common import display_bytes, entry_props, require_key
    from .keys import ENTRY_TYPE_ADDRESS

    app_id, identifier = require_key(msg.app_id, msg.identifier)

    # empty is a legitimate value; absent is not
    value = msg.value
    if value is None:
        raise DataError("value is required")

    key_type = ENTRY_TYPE_ADDRESS

    compact = bool(msg.compact)

    if msg.mac is not None:
        return await _restore(app_id, identifier, key_type, value, msg.mac, compact)

    offline_store.ensure_storable(key_type, app_id, identifier, value)

    status, existing = await offline_store.get(key_type, app_id, identifier)

    props = entry_props(app_id, identifier)
    if status == offline_store.VALID and existing is not None:
        title = "Queue update"
        props.append(("Replaces (local copy)", display_bytes(existing.value), True))
    else:
        title = "Queue new entry"
    props.append(("New value", display_bytes(value), True))
    props.append(
        ("Warning", "Not applied yet. Held on this device until you connect.", False)
    )

    await confirm_properties("ward_queue_entry", title, props)

    # PENDING, not offered: `flush_queue` marks it handed over
    await offline_store.put(key_type, app_id, identifier, value, True, compact=compact)

    return WardQueueSetAck()


async def _restore(
    app_id: str,
    identifier: bytes,
    key_type: str,
    value: bytes,
    mac: bytes,
    compact: bool = False,
) -> "WardQueueSetAck":
    """Put back a queued change this wallet authenticated on the way out.

    VERIFY, THEN SHOW, THEN WRITE: every field written back is under the intent MAC, so a host
    cannot substitute a value or move a key. The user still confirms, and sees what is replaced.

    GAP(ward): NO REPLAY BOUND. The MAC proves this wallet queued these bytes, not that they
    should be queued NOW; a host may re-offer a discarded or already-published change.
    """
    from trezor.messages import WardQueueSetAck
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from . import offline_store
    from .cas import OP_SET, verify_intent_mac
    from .common import display_bytes, entry_props
    from .keys import derive_k_auth, derive_ward_id

    if not verify_intent_mac(
        await derive_k_auth(),
        await derive_ward_id(),
        OP_SET,
        key_type,
        app_id,
        identifier,
        value,
        mac,
    ):
        raise DataError("WARD: this queued change was not authenticated by this wallet")

    offline_store.ensure_storable(key_type, app_id, identifier, value)

    status, existing = await offline_store.get(key_type, app_id, identifier)

    props = entry_props(app_id, identifier)

    if status == offline_store.CORRUPT:
        title = "Replace offline copy?"
        props.append(("Existing", offline_store.UNREADABLE, False))
    elif status == offline_store.VALID and existing is not None and existing.pending:
        title = "Replace pending change?"
        props.append(("Existing pending change", display_bytes(existing.value), True))
    elif status == offline_store.VALID and existing is not None:
        title = "Replace offline copy?"
        props.append(("Existing offline copy", display_bytes(existing.value), True))
    else:
        title = "Restore queued change?"

    props.append(("Restored pending change", display_bytes(value), True))
    props.append(
        (
            "Warning",
            "From a backup. Still not applied -- held until you connect.",
            False,
        )
    )

    await confirm_properties("ward_queue_restore_entry", title, props)

    # PENDING and NOT offered: a restore cannot know whether an earlier publication landed
    await offline_store.put(key_type, app_id, identifier, value, True, compact=compact)

    return WardQueueSetAck()
