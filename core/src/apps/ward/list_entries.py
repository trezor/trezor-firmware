from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDListEntries, WARDListEntriesAck


async def list_entries(msg: WARDListEntries) -> WARDListEntriesAck:
    """WARDListEntries wire handler (TA): show every WARD entry matching the filters
    on-device, walking the trusted root top-down and pulling each node from the host
    (WARDNodeRequest). Only the counts go back to the host.
    """
    from trezor.messages import WARDListEntriesAck

    from apps.common import ward as core

    shown, entries, counter, complete = await core.list_entries(
        msg.app_id, msg.key_type, msg.device_id
    )

    return WARDListEntriesAck(
        shown=shown, entries=entries, counter=counter, complete=complete
    )
