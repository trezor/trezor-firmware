from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import Success, WardGetEntry


async def get_entry(msg: WardGetEntry) -> Success:
    """WardGetEntry handler: show the entry at (app_id, identifier).

    TWO SOURCES, CHOSEN BEFORE ANYTHING IS ASKED. A session that has completed a sync round
    pulls from the host and checks the answer against the root it now trusts. A session that
    has not reads the device's own store instead -- see `apps.ward.offline_store`.

    The choice is made UP FRONT, on `round.is_online()`, and that ordering is the security
    property. If the device pulled first and fell back to its local copy whenever the pull
    failed, a hostile host could force an old value onto the screen simply by answering
    badly: fail the proof, get the cache. Deciding before the request means a verification
    failure has nowhere to fall back to -- it is an error, full stop.

    WHY OFFLINE IS ALSO OFFLINE FOR THE HOST. A host that does not speak WARD cannot answer
    `WardEntryRequest`, so there is nothing to ask; and a host that does but has not synced has
    not shown the device anything current. Both are served locally, and no `WardEntryRequest`
    is emitted at all.

    THREE THINGS THE SCREEN MUST NOT CONFLATE: an entry verified against a trusted root, a
    local copy authenticated at some earlier counter, and a change the user made that no host
    has taken yet. Each gets its own title, because a local copy shown in the wording of a
    verified read is a lie the user has no way to detect.

    GAP(ward): this SHOWS the value and returns only Success -- the plaintext never leaves
    the device. Handing it back to the calling application is a different security model, and
    it collides with unattended use: every read costs a confirmation today, which no
    per-app-settings use-case can pay. Deferred, and coupled to the app_id ACL above: an
    unattended read without a trustworthy app_id is an oracle for any host.
    """
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from . import offline_store
    from . import round as sync_round
    from .common import WARNING_UNVERIFIED, display_bytes, pull_entry, require_key
    from .keys import ENTRY_TYPE_ADDRESS, entry_key_for

    app_id, identifier = require_key(msg.app_id, msg.identifier)

    key_type = ENTRY_TYPE_ADDRESS
    entry_key = await entry_key_for(app_id, identifier, key_type)

    props = [
        ("Domain", app_id, False),
        ("Key", display_bytes(identifier), True),
    ]

    if sync_round.is_online():
        value = await pull_entry(entry_key, key_type)
        # An ABSENT value means "no such entry"; a present-but-empty one is an entry whose
        # value happens to be empty. Keep those distinguishable on screen.
        if value is None:
            title = "Entry not found"
            props.append(("Result", "The host holds no entry for this key.", False))
        else:
            title = "Unverified entry"
            props.append(("Value", display_bytes(value), True))
        props.append(WARNING_UNVERIFIED)
    else:
        status, entry = await offline_store.get(entry_key)

        if status == offline_store.CORRUPT:
            # NOT a miss, and NOT erased. Something is stored here that this build cannot
            # read -- a newer format, or damaged framing -- and reporting "nothing found"
            # would invite writing over it while telling the user it was never there.
            raise DataError("WARD: the offline copy cannot be read")

        if status == offline_store.MISS or entry is None:
            title = "Not kept offline"
            props.append(
                ("Result", "No offline copy. Connect to read this entry.", False)
            )
        elif entry.pending:
            # A change the user confirmed that no host has taken yet. It is what this device
            # believes, not what WARD holds, and saying otherwise would make the earlier
            # confirmation retroactively untrue.
            title = "Pending change"
            props.append(("Value", display_bytes(entry.value), True))
            props.append(
                (
                    "Warning",
                    "Not published yet. Connect to apply this change.",
                    False,
                )
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

    await confirm_properties("ward_get_entry", title, props)

    return Success(message="WARD entry shown")
