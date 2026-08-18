from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import Success, WardEraseCachedEntry


async def erase_cached_entry(msg: WardEraseCachedEntry) -> Success:
    """WardEraseCachedEntry handler: remove this device's local copy, on confirmation.

    THE ONLY WAY A RECORD LEAVES FLASH. Nothing evicts on pressure, expires on age, cleans up
    at boot, or tidies away a record whose format a newer firmware wrote. A record may be
    stale, superseded or unreadable and none of that authorises deleting it -- only this
    screen does. The rule exists because the alternatives all fail the same way: the user
    finds something gone and has no way to learn that anything removed it.

    NOT A WARD DELETION. This erases what the device holds; the entry itself is untouched, and
    `WardDeleteEntry` remains the way to remove one. Two questions -- "stop keeping this here"
    and "this should no longer exist" -- and one confirmation cannot honestly stand for both.
    A host reporting an entry as absent is likewise not permission to erase the local copy;
    the user is asked, here, or nothing happens.

    THE DEVICE DERIVES THE PATH. `entry_key` comes from (app_id, identifier) exactly as every
    other request derives it, so a host cannot name an arbitrary path to destroy -- which is
    the whole reason this is not simply "erase the key I give you".

    SHOW WHAT IS BEING LOST. Confirming a deletion by key alone tells the user nothing about
    what they are giving up, so the value goes on the screen. A pending change gets different
    wording: it was never published, so erasing it DISCARDS a change rather than removing a
    stored value, and calling that "delete" would suggest WARD had it.

    CANCELLATION TOUCHES NOTHING. The delete runs after the confirmation returns, so a
    rejected screen leaves the record byte-for-byte as it was -- `ActionCancelled` propagates
    out before any write.
    """
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_properties

    from . import offline_store
    from .common import display_bytes, require_key
    from .keys import ENTRY_TYPE_ADDRESS, entry_key_for

    app_id, identifier = require_key(msg.app_id, msg.identifier)

    key_type = ENTRY_TYPE_ADDRESS
    entry_key = await entry_key_for(app_id, identifier, key_type)

    status, entry = await offline_store.get(entry_key)

    if status == offline_store.MISS:
        # Nothing here. No screen: a hold-to-confirm that always means "nothing happened" is
        # one that gets approved without being read, and that costs real safety on the paths
        # where holding matters. Same reasoning as the no-op delete in `delete_entry`.
        return Success(message="WARD entry not kept offline")

    props = [
        ("Domain", app_id, False),
        ("Key", display_bytes(identifier), True),
    ]

    if status == offline_store.CORRUPT or entry is None:
        # The escape hatch for a record this build cannot read -- a newer format, or damaged
        # framing. It cannot be shown, so it is named instead. Without this path such a record
        # would be permanently unremovable, which is where a "just wipe it on upgrade"
        # migration gets invented.
        title = "Remove unreadable copy?"
        props.append(
            ("Removing", "An offline copy that cannot be read.", False),
        )
    elif entry.pending:
        title = "Discard pending change?"
        props.append(("Discarding", display_bytes(entry.value), True))
        props.append(
            (
                "Warning",
                "This change was never published. It will be lost.",
                False,
            )
        )
    else:
        title = "Remove offline copy?"
        props.append(("Removing", display_bytes(entry.value), True))
        props.append(
            (
                "Note",
                "The entry itself is not deleted, only this device's copy.",
                False,
            )
        )

    await confirm_properties("ward_erase_cached_entry", title, props, hold=True)

    await offline_store.erase(entry_key)

    return Success(message="WARD offline copy removed")
