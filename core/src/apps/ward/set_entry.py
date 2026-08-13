from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import Success, WARDSetEntry


async def set_entry(msg: WARDSetEntry) -> Success:
    """WARDSetEntry handler: confirm creating or replacing a host-held entry.

    The device pulls the CURRENT value before showing anything, which is what makes an
    add and an overwrite different screens: silently replacing a value the user cannot
    see is the failure mode worth designing against here, so an overwrite names what it
    replaces.

    The device performs no write. On Success the HOST applies the change to its own
    store -- in this phase the device is a confirmation screen, not the writer. That
    inverts in a later phase, when the device becomes the writer and encryptor.
    """
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from .common import WARNING_UNVERIFIED, display_bytes, pull_entry, require_key
    from .keys import entry_key_for

    app_id, identifier = require_key(msg.app_id, msg.identifier)

    # Empty is a legitimate value; absent is not. Writing "nothing specified" as if it
    # were an empty value would silently blank an entry, so require the field.
    value = msg.value
    if value is None:
        raise DataError("value is required")

    old = await pull_entry(await entry_key_for(app_id, identifier))

    props = [
        ("Domain", app_id, False),
        ("Key", display_bytes(identifier), True),
    ]
    if old is None:
        title = "Add entry"
    else:
        title = "Update entry"
        props.append(("Replaces", display_bytes(old), True))
    props.append(("New value", display_bytes(value), True))
    props.append(WARNING_UNVERIFIED)

    await confirm_properties("ward_set_entry", title, props)

    return Success(message="WARD write confirmed")
