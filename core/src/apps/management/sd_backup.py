from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from storage.sd_seed_backup import BackupMedium
    from trezor.enums import BackupType


async def bip39_choose_backup_medium(recovery: bool = False) -> BackupMedium:
    # TODO this will be general, not only for BIP39
    from trezor.ui.layouts import choose_backup_medium

    return await choose_backup_medium(recovery)


async def sdcard_backup_seed(mnemonic_secret: bytes, bak_t: BackupType) -> bool:
    from storage.sd_seed_backup import store_seed_on_sdcard

    from apps.common.sdcard import ensure_sdcard

    await ensure_sdcard(ensure_filesystem=True, for_sd_backup=True)
    return store_seed_on_sdcard(mnemonic_secret, bak_t)


async def sdcard_recover_seed() -> tuple[str | None, BackupType | None]:
    from storage.sd_seed_backup import recover_seed_from_sdcard

    from apps.common.sdcard import ensure_sdcard

    await ensure_sdcard(ensure_filesystem=False)
    mnemonic_bytes, backup_type = recover_seed_from_sdcard()
    if mnemonic_bytes is None or backup_type is None:
        return (None, None)
    return mnemonic_bytes.decode("utf-8"), backup_type
