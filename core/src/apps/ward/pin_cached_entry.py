from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import Success, WardPinCachedEntry


async def pin_cached_entry(msg: WardPinCachedEntry) -> Success:
    """WardPinCachedEntry handler: keep an entry on the device for offline use.

    VERIFY, THEN ASK, THEN WRITE -- in that order, and the order is the design. Persisting
    bytes the device has not yet authenticated would mean a hostile host could fill the store
    with values that later fail to open, and the user would be left deciding what to erase
    among records that were never real. Nothing reaches flash that has not already passed the
    same checks a read passes.

    ONLINE ONLY, like every other read. The value is pulled through `pull_leaf` -- the same
    ask, prove, open that `WardGetEntry` uses -- so what reaches flash is what a verified read
    would have shown: a leaf proved against a WM-attested root this session adopted.

    THIS USED TO ACCEPT AN UNSYNCED DEVICE, at counter 0 with no root, where
    `verify_leaf_against_root` checks nothing and the AEAD was the whole of the evidence. The
    argument for it had two legs and both had gone. "A read in this state already displays
    these bytes" -- `WardGetEntry` now refuses offline, so pinning was the ONLY path left that
    let host bytes in unproved. "The record carries counter 0 and turns stale" -- records store
    no counter (see `offline_store`), so nothing ever marked it. And counter 0 is THIS device's
    floor, not the wallet's: a second device of a wallet with history starts there too, and the
    host holds every leaf that wallet ever published. An authentic OLD address would pin
    cleanly, stay VALID indefinitely, and be served offline as the user's value.

    After a sync that cannot happen. Adoption stores a root before marking the session online
    -- EMPTY_ROOT for a wallet that has never written, which admits no leaf at all -- so there
    is no state left in which a pin is taken on the host's word.

    REPLACEMENT IS DESTRUCTION. An existing record is a value the user chose to keep, so
    overwriting it asks again and shows both values. Identical bytes are the exception: that
    is not a replacement, so it neither prompts nor rewrites flash.
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

    # THE SAME PULL A VERIFIED READ MAKES, not a second copy of it. Proved against the root this
    # session adopted -- so a genuine but OLDER leaf fails to be in it, which is the whole of the
    # anti-rollback here: `WardEntryAck` carries no counter, deliberately, since a host-asserted
    # one would be worth nothing. It is also where the host is refused a say in the key_type.
    value, _leaf, _material = await pull_leaf(entry_key, key_type)
    if value is None:
        # A proved absence, or a tombstone. Nothing to keep, and inventing an empty record
        # would make a later offline read report a value the entry does not have.
        raise DataError("WARD: no entry to keep offline")

    # SIZE IS REFUSED BEFORE THE PROMPT. Asking the user to keep something and then failing to
    # store it wastes a confirmation and teaches them the screen means nothing. The online read
    # is unaffected -- an entry too large to keep is still perfectly readable.
    #
    # Both caps, via one authority: the value cap alone would let a long app_id or identifier push a
    # legal value past the RECORD cap and fail after the hold. See `offline_store.ensure_storable`.
    offline_store.ensure_storable(key_type, app_id, identifier, value)

    status, existing = await offline_store.get(key_type, app_id, identifier)

    if status == offline_store.VALID and existing is not None:
        if existing.value == value:
            # SAME VALUE, so nothing at all happens: nothing is being destroyed, and a hold that
            # always means "keep what you already have" is a screen that gets approved without being
            # read.
            #
            # This used to REFRESH the record, rewriting it at the current counter so a still-current
            # copy would stop reading as stale. No counter is stored now, so there is nothing to
            # refresh -- and one fewer reason to write to flash.
            return Success(message="WARD entry already kept offline")

        await confirm_properties(
            "ward_replace_cached_entry",
            "Replace offline copy?",
            [
                ("Domain", app_id, False),
                ("Key", display_bytes(identifier), True),
                ("Replacing", display_bytes(existing.value), True),
                ("With", display_bytes(value), True),
            ],
            hold=True,
        )
    elif status == offline_store.CORRUPT:
        # Something unreadable occupies this path. Overwriting it silently would destroy a
        # record the user was never told about, so this is a replacement like any other --
        # named as unreadable, since its value cannot be shown.
        await confirm_properties(
            "ward_replace_cached_entry",
            "Replace offline copy?",
            [
                ("Domain", app_id, False),
                ("Key", display_bytes(identifier), True),
                ("Replacing", "An offline copy that cannot be read.", False),
                ("With", display_bytes(value), True),
            ],
            hold=True,
        )
    else:
        await confirm_properties(
            "ward_pin_cached_entry",
            "Keep for offline use?",
            [
                ("Domain", app_id, False),
                ("Key", display_bytes(identifier), True),
                ("Value", display_bytes(value), True),
                (
                    "Note",
                    "Kept on this device until you remove it.",
                    False,
                ),
            ],
        )

    # NOT pending: this is a copy of a value WARD already holds, proved against the trusted root
    # above, not a change waiting to be published.
    await offline_store.put(key_type, app_id, identifier, value, False)

    return Success(message="WARD entry kept offline")
