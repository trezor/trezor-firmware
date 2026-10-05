from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardQueueDeleteAck, WardQueueDeleteEntry


async def queue_delete_entry(msg: WardQueueDeleteEntry) -> WardQueueDeleteAck:
    """WardQueueDeleteEntry handler: DISCARD a queued (pending) change, on a held confirmation.

    Not a WARD deletion, and never touches a pinned copy (`WardEraseCachedEntry` does that).
    Nothing queued -- or unreadable -- is reported as `missing`, with no screen and no erase.
    """
    from trezor.messages import WardQueueDeleteAck
    from trezor.ui.layouts import confirm_properties

    from . import offline_store
    from .common import display_bytes, entry_props

    app_id, identifier, key_type, status, entry = await offline_store.lookup(msg)

    if status != offline_store.VALID or entry is None or not entry.pending:
        return WardQueueDeleteAck(missing=True)

    await confirm_properties(
        "ward_queue_delete_entry",
        "Discard queued change?",
        entry_props(app_id, identifier)
        + [
            ("Discarding", display_bytes(entry.value), True),
            ("Warning", "This change was never published. It will be lost.", False),
        ],
        hold=True,
    )

    await offline_store.erase(key_type, app_id, identifier)

    return WardQueueDeleteAck()
