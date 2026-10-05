from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import Success, WardEraseCachedEntry


async def erase_cached_entry(msg: WardEraseCachedEntry) -> Success:
    """WardEraseCachedEntry handler: remove this device's local copy, on a held confirmation.

    The only way a record leaves flash, including one this build cannot read. Not a WARD deletion.
    The screen shows what is lost; nothing is written unless the user confirms.
    """
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_properties

    from . import offline_store
    from .common import display_bytes

    app_id, identifier, key_type, status, entry = await offline_store.lookup(msg)

    if status == offline_store.MISS:
        return Success(message="WARD entry not kept offline")

    props = offline_store.entry_props(app_id, identifier)
    unreadable = status == offline_store.CORRUPT or entry is None

    if unreadable:
        title = "Remove unreadable copy?"
        props.append(("Removing", offline_store.UNREADABLE, False))
    elif entry.pending:
        title = "Discard pending change?"
        props.append(("Discarding", display_bytes(entry.value), True))
        props.append(
            ("Warning", "This change was never published. It will be lost.", False)
        )
    else:
        title = "Remove offline copy?"
        props.append(("Removing", display_bytes(entry.value), True))
        props.append(
            ("Note", "The entry itself is not deleted, only this device's copy.", False)
        )

    await confirm_properties("ward_erase_cached_entry", title, props, hold=True)

    if unreadable:
        # cannot be named, so it goes by slot
        if not await offline_store.erase_unreadable():
            return Success(message="WARD entry not kept offline")
    else:
        await offline_store.erase(key_type, app_id, identifier)

    return Success(message="WARD offline copy removed")
