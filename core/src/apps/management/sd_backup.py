from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from storage.sd_seed_backup import BackupMedium
    from trezor.enums import BackupType


async def choose_recovery_medium(is_slip39: bool, dry_run: bool) -> BackupMedium:
    from trezor.ui.layouts import choose_recovery_medium

    return await choose_recovery_medium(is_slip39, dry_run)

async def choose_backup_medium(
    share_index: int | None, group_index: int | None, recovery: bool = False
) -> BackupMedium:
    from trezor.ui.layouts import choose_backup_medium

    return await choose_backup_medium(share_index, group_index)


async def sdcard_backup_seed(mnemonic_secret: bytes, backup_type: BackupType):
    from storage.sd_seed_backup import store_seed_on_sdcard, is_backup_present
    from apps.common.sdcard import ensure_sdcard
    from trezor.ui.layouts import confirm_action, show_success

    await ensure_sdcard(ensure_filesystem=False)
    if is_backup_present():
        await confirm_action(
            "warning_sdcard_backup_exists",
            "Backup present",
            action="There is already a Trezor backup on this card!",
            description="Replace the backup?",
            verb="Replace",
            verb_cancel="Abort",
            hold=True,
            hold_danger=True,
            reverse=True,
        )
    await ensure_sdcard(ensure_filesystem=True, for_sd_backup=True)

    store_seed_on_sdcard(mnemonic_secret, backup_type)

    await show_success("success_sdcard_backup", "Backup on SD card successful!")


async def sdcard_recover_seed() -> tuple[str | None, BackupType | None]:
    from storage.sd_seed_backup import recover_seed_from_sdcard
    from apps.common.sdcard import ensure_sdcard

    await ensure_sdcard(ensure_filesystem=False)
    mnemonic_bytes, backup_type = recover_seed_from_sdcard()
    if mnemonic_bytes is None or backup_type is None:
        return (None, None)
    return mnemonic_bytes.decode("utf-8"), backup_type
