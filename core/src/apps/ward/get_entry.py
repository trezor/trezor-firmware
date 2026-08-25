from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import Success, WardGetEntry


async def get_entry(msg: WardGetEntry) -> Success:
    """WardGetEntry handler: pull the entry at (app_id, identifier) and show it.

    REQUIRES A SYNCED SESSION AND REFUSES WITHOUT ONE. It used to fall back to the device's own
    store, which made this request mean two different things -- a verified read, or a local copy
    -- depending on state the host cannot see. Reading what the device holds is now asked for by
    name: `WardQueueGetEntry`.

    THE REFUSAL IS ALSO THE SECURITY PROPERTY, and it is stronger than the fallback was. A
    device that pulled first and used its local copy whenever the pull failed would let a
    hostile host force an old value onto the screen simply by answering badly: fail the proof,
    get the cache. Here a verification failure has nowhere to go -- it is an error, full stop --
    and the offline read is a separate request the user's host had to choose.

    THE SCREEN IS THE OUTPUT CHANNEL, and `confirm_properties` below carries the value among its
    properties -- so by the time the user is asked, the secret is already on the display. That is
    an acknowledgement, not a decision, and it is safe only because `apps.ward.app_role` has
    already decided that exactly one application may trigger a read. On a transport with no app
    role the filter asks first instead; see `app_role.require_ward_app`.

    GAP(ward): this SHOWS the value and returns only Success -- the plaintext never leaves
    the device. Handing it back to the calling application is a different security model, and
    it collides with unattended use: every read costs a confirmation today, which no
    per-app-settings use-case can pay. Deferred, and coupled to the app_id ACL above: an
    unattended read without a trustworthy app_id is an oracle for any host.
    """
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from .common import (
        WARNING_UNVERIFIED,
        display_bytes,
        online,
        pull_entry,
        require_key,
    )
    from .keys import ENTRY_TYPE_ADDRESS, entry_key_for

    app_id, identifier = require_key(msg.app_id, msg.identifier)

    key_type = ENTRY_TYPE_ADDRESS
    entry_key = await entry_key_for(app_id, identifier, key_type)

    props = [
        ("Domain", app_id, False),
        ("Key", display_bytes(identifier), True),
    ]

    if not await online():
        raise DataError("WARD: sync first, or read the local copy with WardQueueGetEntry")

    value = await pull_entry(entry_key, key_type)
    # An ABSENT value means "no such entry"; a present-but-empty one is an entry whose value
    # happens to be empty. Keep those distinguishable on screen.
    if value is None:
        title = "Entry not found"
        props.append(("Result", "The host holds no entry for this key.", False))
    else:
        title = "Unverified entry"
        props.append(("Value", display_bytes(value), True))
    props.append(WARNING_UNVERIFIED)

    await confirm_properties("ward_get_entry", title, props)

    return Success(message="WARD entry shown")
