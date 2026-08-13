from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDLeafAck, WARDSetEntry


async def set_entry(msg: WARDSetEntry) -> WARDLeafAck:
    """WARDSetEntry handler: confirm creating or replacing a host-held entry.

    The device pulls the CURRENT value before showing anything, which is what makes an
    add and an overwrite different screens: silently replacing a value the user cannot
    see is the failure mode worth designing against here, so an overwrite names what it
    replaces.

    The device then BUILDS THE LEAF and returns it; the host stores it verbatim under
    entry_key and applies the change to its own store. The device keeps nothing. It has
    to be the builder because it is the only party that will hold the keys once the parts
    are sealed -- so the host is never given a leaf-shaped thing it is expected to
    assemble itself.
    """
    from trezor.messages import WARDLeafAck
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from .common import WARNING_UNVERIFIED, display_bytes, pull_leaf, require_key
    from .keys import ENTRY_TYPE_ADDRESS, derive_k_data, derive_k_ident, entry_key_for
    from .leaf import encode_content, encode_identity, make_leaf_content, make_leaf_identity
    from .root import get_root, set_root
    from .trie import compute_new_root

    app_id, identifier = require_key(msg.app_id, msg.identifier)

    # Empty is a legitimate value; absent is not. Writing "nothing specified" as if it
    # were an empty value would silently blank an entry, so require the field.
    value = msg.value
    if value is None:
        raise DataError("value is required")

    key_type = ENTRY_TYPE_ADDRESS
    entry_key = await entry_key_for(app_id, identifier, key_type)
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
    id_part = encode_identity(
        await derive_k_ident(key_type), entry_key, key_type, identifier, app_id
    )
    val_part = encode_content(await derive_k_data(key_type), entry_key, key_type, value)

    # The device DERIVES its own new root rather than being told one. That is what makes
    # the root worth anything: it is a value the device computed from a state the host had
    # to prove, not a number it was handed.
    proof, witness_entry_key, witness_commit, _sibling = material
    new_root = compute_new_root(
        entry_key,
        old_leaf,
        (key_type, id_part, val_part),
        proof,
        get_root(),
        witness_entry_key=witness_entry_key,
        witness_commit=witness_commit,
    )
    set_root(new_root)

    return WARDLeafAck(
        entry_key=entry_key,
        identity=make_leaf_identity(key_type, id_part),
        content=make_leaf_content(val_part),
    )
