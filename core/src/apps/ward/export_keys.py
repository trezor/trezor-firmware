from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDExportKeys, WARDExportKeysAck


async def export_keys(msg: WARDExportKeys) -> WARDExportKeysAck:
    """WARDExportKeys wire handler (TA): PUSH key export. After on-device user
    confirmation the trust anchor returns K_path + K_ident/K_data(key_type), three
    independent capabilities: resolve identifier -> path, read identities, read
    values. K_sig is never exported. Note the host does NOT need any of these to
    locate a leaf or serve a proof -- the MAC is stored with the leaf. The host is
    expected to hold the keys in memory only.
    """
    from trezor.messages import WARDExportKeysAck

    from apps.common import ward as core

    key_type = msg.key_type or "address"
    k_path, k_data, k_ident = await core.export_keys(key_type)

    return WARDExportKeysAck(
        k_path=k_path, k_data=k_data, k_ident=k_ident, key_type=key_type
    )
