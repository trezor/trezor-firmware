from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import Success, WardGetEntry


async def get_entry(msg: WardGetEntry) -> Success:
    """WardGetEntry handler: PULL a plaintext entry from the host and show it.

    The device holds no entries, so it asks the host for this one and renders what it
    gets. See `common.pull_entry`; the value is UNAUTHENTICATED in this phase, hence
    `WARNING_UNVERIFIED` on the screen.

    GAP(ward): this SHOWS the value and returns only Success -- the plaintext never leaves
    the device. Handing it back to the calling application is a different security model, and
    it collides with unattended use: every read costs a confirmation today, which no
    per-app-settings use-case can pay. Deferred, and coupled to the app_id ACL above: an
    unattended read without a trustworthy app_id is an oracle for any host.
    """
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_properties

    from .common import WARNING_UNVERIFIED, display_bytes, pull_entry, require_key
    from .keys import ENTRY_TYPE_ADDRESS, entry_key_for

    app_id, identifier = require_key(msg.app_id, msg.identifier)

    key_type = ENTRY_TYPE_ADDRESS
    entry_key = await entry_key_for(app_id, identifier, key_type)
    value = await pull_entry(entry_key, key_type)

    # An ABSENT value means "no such entry"; a present-but-empty one is an entry whose
    # value happens to be empty. Keep those distinguishable on screen.
    props = [
        ("Domain", app_id, False),
        ("Key", display_bytes(identifier), True),
    ]
    if value is None:
        title = "Entry not found"
        props.append(("Result", "The host holds no entry for this key.", False))
    else:
        title = "Unverified entry"
        props.append(("Value", display_bytes(value), True))
    props.append(WARNING_UNVERIFIED)

    await confirm_properties("ward_get_entry", title, props)

    return Success(message="WARD entry shown")
