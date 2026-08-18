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

    WHAT IS CHECKED DEPENDS ON WHAT THE DEVICE KNOWS, and `verify_leaf_against_root` already
    encodes exactly that, which is why this calls it with the same arguments a read would
    rather than growing a second policy that could drift:

      counter > 0 : a Merkle proof against the trusted root, plus the anti-rollback floor
                    below. The leaf is bound to a tree the device accepted.

      counter = 0 : nothing to check against, so nothing is checked. There is no trie on the
                    host yet, hence no proof and no root -- and a proof against a root the
                    host supplied would be theatre.

    WHAT COUNTER 0 STILL BUYS, because it is not nothing. The AEAD opens or it does not, and
    its AAD is domain || entry_key || key_type: only a holder of K_data -- this wallet's
    devices, nobody else -- can produce a valid tag. A host cannot forge a value, move a leaf
    to another path, or pass an identity part off as a content part. What it CANNOT show is
    freshness: a genuine older leaf for this path passes identically, and nothing here can
    tell the two apart.

    So pinning at counter 0 adds NO NEW TRUST ASSUMPTION. A read in this state already
    displays exactly these bytes on exactly this evidence; the store keeps what the screen
    already showed. The record carries counter 0, which turns it stale the moment a reconcile
    moves the trusted counter off zero -- so it can never later pass for current.

    REPLACEMENT IS DESTRUCTION. An existing record is a value the user chose to keep, so
    overwriting it asks again and shows both values. Identical bytes are the exception: that
    is not a replacement, so it neither prompts nor rewrites flash.
    """
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from . import offline_store
    from .common import (
        decode_leaf,
        display_bytes,
        pull_leaf_from_host,
        require_key,
        verify_leaf_against_root,
    )
    from .keys import ENTRY_TYPE_ADDRESS, entry_key_for
    from .leaf import is_delete, read_leaf_content, read_leaf_identity
    from .root import get_counter, get_root

    app_id, identifier = require_key(msg.app_id, msg.identifier)

    key_type = ENTRY_TYPE_ADDRESS
    entry_key = await entry_key_for(app_id, identifier, key_type)

    ack = await pull_leaf_from_host(entry_key)
    val_part = read_leaf_content(ack.content)
    wire_key_type, id_part = read_leaf_identity(ack.identity)
    present = val_part is not None and not is_delete(val_part)
    leaf_key_type = wire_key_type or key_type

    trusted_root = await get_root()
    trusted_counter = await get_counter()

    verify_leaf_against_root(
        trusted_root,
        trusted_counter,
        entry_key,
        leaf_key_type,
        id_part,
        val_part,
        present,
        ack.proof,
        ack.witness_entry_key,
        ack.witness_commit,
    )

    if not present:
        # A proved absence. Nothing to keep, and inventing an empty record would make a later
        # offline read report a value the entry does not have.
        raise DataError("WARD: no entry to keep offline")

    # ANTI-ROLLBACK IS THE PROOF, and there is nothing else to add here. `WardEntryAck` carries
    # no counter -- deliberately, since a host-asserted one would be worth nothing -- so a leaf
    # from an earlier state is caught by failing to be IN the trusted root, above. Being
    # authentic is not the same as being current, and the membership check is what separates
    # them. At counter 0 there is no root, so no such separation exists; see below.

    value = await decode_leaf(entry_key, key_type, val_part)
    if value is None:
        raise DataError("WARD: no entry to keep offline")

    # SIZE IS REFUSED BEFORE THE PROMPT. Asking the user to keep something and then failing to
    # store it wastes a confirmation and teaches them the screen means nothing. The online read
    # is unaffected -- an entry too large to keep is still perfectly readable.
    from storage.ward import MAX_VALUE_LEN

    if len(value) > MAX_VALUE_LEN:
        raise DataError("WARD: entry too large to keep offline")

    status, existing = await offline_store.get(entry_key)

    if status == offline_store.VALID and existing is not None:
        if existing.value == value:
            # SAME VALUE. Nothing is being destroyed, so there is nothing to authorise: a
            # hold that always means "keep what you already have" is a screen that gets
            # approved without being read.
            #
            # The counter may still have moved, and refreshing it is not a replacement -- it
            # records that this same value was seen again at a later confirmed state, which
            # is what stops a perfectly current copy from reading as stale forever. Compared
            # on the VALUE rather than on the record bytes for exactly that reason: the two
            # differ whenever the counter has advanced, which would otherwise make every
            # refresh look like a destructive overwrite.
            if existing.counter == trusted_counter:
                return Success(message="WARD entry already kept offline")
            await offline_store.put(
                entry_key,
                key_type,
                app_id,
                identifier,
                0,
                value,
                trusted_counter,
                False,
            )
            return Success(message="WARD offline copy refreshed")

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

    await offline_store.put(
        entry_key,
        key_type,
        app_id,
        identifier,
        0,
        value,
        trusted_counter,
        False,
    )

    return Success(message="WARD entry kept offline")
