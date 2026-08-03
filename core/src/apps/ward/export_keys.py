from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDExportKeys, WARDExportKeysAck


async def export_keys(msg: WARDExportKeys) -> WARDExportKeysAck:
    """WARDExportKeys wire handler (TA): PUSH key export. After on-device user
    confirmation the trust anchor returns K_index + K_data(key_type) so the host can
    compute entry_key paths and encrypt/decrypt values for the requested entry type
    itself. K_sig is never exported. The host is expected to hold the keys in memory
    only.
    """
    from trezor.messages import WARDExportKeysAck

    from apps.common import ward as core

    key_type = msg.key_type or "address"
    k_index, k_data = await core.export_keys(key_type)

    return WARDExportKeysAck(k_index=k_index, k_data=k_data, key_type=key_type)
