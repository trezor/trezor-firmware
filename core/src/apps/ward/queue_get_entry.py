from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardQueueGetAck, WardQueueGetEntry


async def queue_get_entry(msg: WardQueueGetEntry) -> WardQueueGetAck:
    """WardQueueGetEntry handler: EXPORT what the device holds, on confirmation, for backup.

    No pull: this reads only the device's own store. A pending change comes back with an intent MAC
    under K_auth, so `queue_set_entry` can restore it without the host being able to forge one; a
    pinned copy gets no MAC (there is no intent to re-queue). An unreadable record FAILS rather than
    reading as missing. The blob is deliberately plaintext.

    The value is on the screen before the user answers, so on a transport with no app role the
    filter must ask first (see `apps.ward.app_role`).
    """
    from trezor.messages import WardQueueGetAck
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from . import offline_store
    from .cas import OP_SET, intent_mac
    from .common import display_bytes
    from .keys import derive_k_auth, derive_ward_id

    app_id, identifier, _key_type, status, entry = await offline_store.lookup(msg)

    props = offline_store.entry_props(app_id, identifier)

    if status == offline_store.CORRUPT or (status == offline_store.VALID and entry is None):
        raise DataError("WARD: the offline copy cannot be read")

    if status == offline_store.MISS or entry is None:
        title = "Not kept offline"
        props.append(("Result", "No offline copy. Connect to read this entry.", False))
        ack = WardQueueGetAck(missing=True)
    else:
        props.append(("Value", display_bytes(entry.value), True))
        ack = WardQueueGetAck(
            key_type=entry.key_type,
            app_id=entry.app_id,
            identifier=entry.identifier,
            value=entry.value,
        )
        if entry.pending:
            title = "Back up queued change?"
            warning = "Not published yet. The value is sent to the host so it can be restored."
            ack.pending = True
            ack.mac = intent_mac(
                await derive_k_auth(),
                await derive_ward_id(),
                OP_SET,
                entry.key_type,
                entry.app_id,
                entry.identifier,
                entry.value,
            )
        else:
            title = "Send offline copy?"
            warning = "Local copy, not checked against the host. It may be out of date."
        props.append(("Warning", warning, False))

    await confirm_properties("ward_queue_get_entry", title, props)

    return ack
