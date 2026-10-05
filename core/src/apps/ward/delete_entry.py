from typing import TYPE_CHECKING

from trezor import utils

if TYPE_CHECKING:
    from trezor.messages import WardDeleteEntry, WardLeafAck, WardMutationApplied


async def delete_entry(msg: WardDeleteEntry) -> "WardLeafAck | WardMutationApplied":
    """WardDeleteEntry handler: hold to confirm removing an entry; returns a leaf with BOTH
    PARTS EMPTY, the host's signal to delete the row.

    IDEMPOTENT ON A PROVED ABSENCE: `pull_leaf` has already checked a non-membership witness, so
    an already-absent entry succeeds with no screen, no counter change and no authorisation.

    REQUIRES A CONNECTION. `EMPTY_PART` is plaintext, so any host can build a delete leaf; a
    queued delete would need a sealed tombstone and an intent MAC, which do not exist yet.

    NEVER TOUCHES THE OFFLINE COPY: that is `WardEraseCachedEntry`, a separate consent.
    """
    from trezor.messages import WardLeafAck
    from trezor.ui.layouts import confirm_properties
    from trezor.wire import DataError

    from .common import (
        WARNING_UNVERIFIED,
        commit_change,
        display_bytes,
        entry_props,
        online,
        pull_leaf,
        require_key,
    )
    from .keys import ENTRY_TYPE_ADDRESS, entry_key_for
    from .leaf import EMPTY_PART, make_leaf_content, make_leaf_identity
    from .root import get_counter

    app_id, identifier = require_key(msg.app_id, msg.identifier)

    if not await online():
        raise DataError("WARD: connect to delete an entry")

    key_type = ENTRY_TYPE_ADDRESS
    entry_key = await entry_key_for(app_id, identifier, key_type)
    current, old_leaf, material = await pull_leaf(entry_key, key_type)
    if current is None:
        # No transition, so no authorisation of either kind: a host branches on the missing
        # `auth_commit`. A service build must not drop the online latch or file a claim either.
        counter = await get_counter()
        if utils.USE_WARD_SERVICE_CHANNEL:
            from trezor.messages import WardMutationApplied

            return WardMutationApplied(entry_key=entry_key, counter=counter)

        return WardLeafAck(
            entry_key=entry_key,
            identity=make_leaf_identity(key_type, EMPTY_PART),
            content=make_leaf_content(EMPTY_PART),
            counter=counter,
        )

    props = entry_props(app_id, identifier)
    props.append(("Deleting value", display_bytes(current), True))
    props.append(WARNING_UNVERIFIED)

    await confirm_properties("ward_delete_entry", "Delete entry", props, hold=True)

    return await commit_change(
        entry_key, key_type, app_id, identifier, None, old_leaf, material
    )
