from trezor import io, utils

from storage.sd_seed_backup import store_seed_on_sdcard, recover_seed_from_sdcard

if utils.USE_SD_CARD:
    fatfs = io.fatfs  # global_import_cache

async def bip39_choose_backup_medium(recovery: bool = False) -> str:
    # TODO this will be general, not only for BIP39
    from trezor.ui.layouts import choose_backup_medium

    return await choose_backup_medium(recovery)


async def sdcard_backup_seed(mnemonic_secret: bytes) -> bool:
    from apps.common.sdcard import ensure_sdcard

    await ensure_sdcard(ensure_filesystem=True, for_sd_backup=True)
    return store_seed_on_sdcard(mnemonic_secret)


async def sdcard_recover_seed() -> str | None:
    from apps.common.sdcard import ensure_sdcard

    await ensure_sdcard(ensure_filesystem=False)
    seed_read = recover_seed_from_sdcard()
    return seed_read
