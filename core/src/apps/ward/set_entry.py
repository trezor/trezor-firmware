from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WardLeafAck, WardSetEntry


async def set_entry(msg: WardSetEntry) -> WardLeafAck:
    """WardSetEntry handler: confirm creating or replacing a host-held entry.

    The device pulls the CURRENT value before showing anything, which is what makes an
    add and an overwrite different screens: silently replacing a value the user cannot
    see is the failure mode worth designing against here, so an overwrite names what it
    replaces.

    The device then BUILDS THE LEAF and returns it; the host stores it verbatim under
    entry_key and applies the change to its own store. It has to be the builder because it is
    the only party that will hold the keys once the parts are sealed -- so the host is never
    given a leaf-shaped thing it is expected to assemble itself.

    WITH NO SYNCED HOST THE CHANGE IS QUEUED INSTEAD. The device cannot pull, so it cannot
    prove current state, cannot derive a root and cannot stamp a counter -- there is no leaf to
    build and nothing honest to return. It stores the intent and says so, and the change is
    sealed and published later by `flush_queue`.

    The screen has to say QUEUED rather than done. A confirmation that reads as "applied" when
    nothing has been applied is the failure `storage/ward.py` warns about: the user holds, the
    change sits in flash, and they have no reason to think anything is outstanding.
    """
    from trezor.messages import WardLeafAck
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from . import round as sync_round
    from .attest import root_mac
    from .cas import auth_commit, sig_commit
    from .common import WARNING_UNVERIFIED, display_bytes, pull_leaf, require_key
    from .keys import (
        ENTRY_TYPE_ADDRESS,
        derive_k_auth,
        derive_k_data,
        derive_k_ident,
        derive_k_mac,
        derive_k_sig,
        derive_ward_id,
        entry_key_for,
    )
    from .leaf import (
        encode_content,
        encode_identity,
        make_leaf_content,
        make_leaf_identity,
    )
    from .root import get_counter, get_root
    from .trie import compute_new_root

    app_id, identifier = require_key(msg.app_id, msg.identifier)

    # Empty is a legitimate value; absent is not. Writing "nothing specified" as if it
    # were an empty value would silently blank an entry, so require the field.
    value = msg.value
    if value is None:
        raise DataError("value is required")

    key_type = ENTRY_TYPE_ADDRESS
    entry_key = await entry_key_for(app_id, identifier, key_type)

    if not sync_round.is_online():
        return await _queue_offline(app_id, identifier, entry_key, key_type, value)

    old, old_leaf, material = await pull_leaf(entry_key, key_type)

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

    # Sealed only after confirmation, so a rejected write produces no leaf at all -- and
    # burns no nonce.
    #
    # The counter advances here, and the leaf is stamped with the counter it was written
    # at (C_leaf). Nothing reads that stamp yet; it exists so a later per-leaf staleness
    # check has something to compare, and writing it now costs nothing while leaving it
    # zero would mean rewriting every leaf to add it.
    from_root = await get_root()
    counter = await get_counter() + 1
    id_part = encode_identity(
        await derive_k_ident(key_type), entry_key, key_type, identifier, app_id
    )
    val_part = encode_content(
        await derive_k_data(key_type), entry_key, key_type, value, c_leaf=counter
    )

    # The device DERIVES its own new root rather than being told one. That is what makes
    # the root worth anything: it is a value the device computed from a state the host had
    # to prove, not a number it was handed.
    proof, witness_entry_key, witness_commit = material
    new_root = compute_new_root(
        entry_key,
        old_leaf,
        (key_type, id_part, val_part),
        proof,
        from_root,
        witness_entry_key=witness_entry_key,
        witness_commit=witness_commit,
    )
    # NOT COMMITTED HERE. The device hands back the root it derived, its counter and the
    # authenticators; the head only moves when a WM attestation names that counter and a mac
    # the device can reproduce -- see `reconcile`. That is what makes "the head is always a
    # state the WM confirmed" an invariant, and it is what the fork check exists in spite of:
    # two devices can no longer both hold an unconfirmed counter N+1, because neither holds
    # one at all. Nothing needs storing in the meantime -- the mac is self-validating, so the
    # device can accept the root later purely because it reproduces the attested mac.

    return WardLeafAck(
        entry_key=entry_key,
        identity=make_leaf_identity(key_type, id_part),
        content=make_leaf_content(val_part),
        counter=counter,
        mac=root_mac(await derive_k_mac(), await derive_ward_id(), counter, new_root),
        auth_commit=auth_commit(
            await derive_k_auth(),
            await derive_ward_id(),
            counter - 1,
            from_root,
            counter,
            new_root,
        ),
        auth_sig=sig_commit(
            await derive_k_sig(),
            await derive_ward_id(),
            counter - 1,
            from_root,
            counter,
            new_root,
        ),
    )


async def _queue_offline(
    app_id: str,
    identifier: bytes,
    entry_key: bytes,
    key_type: str,
    value: bytes,
) -> "WardLeafAck":
    """Hold the change on the device until a synced host can take it.

    The old value shown is the device's own copy if it has one. That is weaker than the online
    screen, which shows what the host proved -- so it is labelled as a local copy rather than
    presented as the current value. Showing nothing would be worse: an overwrite the user
    cannot see is the failure the online path already designs against, and being offline does
    not make it less true.

    The ack carries `queued` and NOTHING ELSE of substance -- no counter, no mac, no
    auth_commit. Their absence is the honest report: none of them exists yet, because none can
    be derived without current state. A host must not mistake this for a write it can store.
    """
    from trezor.messages import WardLeafAck
    from trezor.ui.layouts import confirm_properties

    from . import offline_store
    from .common import display_bytes

    status, existing = await offline_store.get(entry_key)

    props = [
        ("Domain", app_id, False),
        ("Key", display_bytes(identifier), True),
    ]
    if status == offline_store.VALID and existing is not None:
        title = "Queue update"
        props.append(("Replaces (local copy)", display_bytes(existing.value), True))
    else:
        title = "Queue new entry"
    props.append(("New value", display_bytes(value), True))
    props.append(
        (
            "Warning",
            "Not applied yet. Held on this device until you connect.",
            False,
        )
    )

    await confirm_properties("ward_queue_entry", title, props)

    # Stored only after confirmation, and with counter 0 -- "no counter assigned". The counter
    # is stamped by `flush_queue` when the change is finally derived against a real root.
    await offline_store.put(
        entry_key,
        key_type,
        app_id,
        identifier,
        0,
        value,
        0,
        True,
    )

    return WardLeafAck(entry_key=entry_key, queued=True)
