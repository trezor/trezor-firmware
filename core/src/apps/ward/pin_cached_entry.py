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
    from .common import display_bytes, entry_props, online, read_entry, require_key
    from .keys import ENTRY_TYPE_ADDRESS

    app_id, identifier = require_key(msg.app_id, msg.identifier)

    key_type = ENTRY_TYPE_ADDRESS

    if not await online():
        raise DataError("WARD: sync first; an entry is kept offline only once it is proved")

    # A pointer is kept as the value it resolves to: the offline copy is what a read returns.
    value, _target = await read_entry(app_id, identifier)
    if value is None:
        raise DataError("WARD: no entry to keep offline")

    # before the prompt, so a confirmation is never wasted on something that cannot be stored
    offline_store.ensure_storable(key_type, app_id, identifier, value)

    status, existing = await offline_store.get(key_type, app_id, identifier)
    props = entry_props(app_id, identifier)

    if status == offline_store.VALID and existing is not None and existing.value == value:
        return Success(message="WARD entry already kept offline")
    replacing = offline_store.existing_value(status, existing)

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
