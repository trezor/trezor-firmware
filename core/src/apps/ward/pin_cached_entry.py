from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import Success, WardPinCachedEntry


async def pin_cached_entry(msg: WardPinCachedEntry) -> Success:
    """WardPinCachedEntry handler: keep an entry on the device for offline use.

    VERIFY, THEN ASK, THEN WRITE. Online only: the value comes through the same proved pull a read
    uses, against the root this session adopted, so nothing unproved reaches flash. Replacing a
    different kept value is destructive and asks with a hold; identical bytes are a no-op.
    """
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from . import offline_store
    from .common import display_bytes, online, pull_leaf, require_key
    from .keys import ENTRY_TYPE_ADDRESS, entry_key_for

    app_id, identifier = require_key(msg.app_id, msg.identifier)

    key_type = ENTRY_TYPE_ADDRESS
    entry_key = await entry_key_for(app_id, identifier, key_type)

    if not await online():
        raise DataError("WARD: sync first; an entry is kept offline only once it is proved")

    value, _leaf, _material = await pull_leaf(entry_key, key_type)
    if value is None:
        raise DataError("WARD: no entry to keep offline")

    # before the prompt, so a confirmation is never wasted on something that cannot be stored
    offline_store.ensure_storable(key_type, app_id, identifier, value)

    status, existing = await offline_store.get(key_type, app_id, identifier)
    props = offline_store.entry_props(app_id, identifier)

    if status == offline_store.VALID and existing is not None:
        if existing.value == value:
            return Success(message="WARD entry already kept offline")
        replacing = (display_bytes(existing.value), True)
    elif status == offline_store.CORRUPT:
        replacing = (offline_store.UNREADABLE, False)
    else:
        replacing = None

    if replacing is not None:
        await confirm_properties(
            "ward_replace_cached_entry",
            "Replace offline copy?",
            props
            + [("Replacing",) + replacing, ("With", display_bytes(value), True)],
            hold=True,
        )
    else:
        await confirm_properties(
            "ward_pin_cached_entry",
            "Keep for offline use?",
            props
            + [
                ("Value", display_bytes(value), True),
                ("Note", "Kept on this device until you remove it.", False),
            ],
        )

    await offline_store.put(key_type, app_id, identifier, value, False)

    return Success(message="WARD entry kept offline")
