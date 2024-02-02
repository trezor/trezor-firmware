from typing import TYPE_CHECKING

from storage.device import is_initialized
from trezor.utils import USE_SD_CARD
from trezor.wire import NotInitialized, ProcessError
from trezor.enums import SdCardBackupManageOperationType
from trezor.ui.layouts import confirm_action

from apps.common.sdcard import ensure_sdcard
from trezor.messages import (
    Success,
    Failure,
)

if TYPE_CHECKING:
    from trezor.messages import (
        SdCardBackupManage,
        SdCardBackupHealth,
    )


# NOTE: this whole functionality is WIP
async def sd_backup_manage(
    msg: SdCardBackupManage,
) -> Success | Failure | SdCardBackupHealth:
    if not is_initialized():
        raise NotInitialized("Device is not initialized")

    if not USE_SD_CARD:
        raise ProcessError("Device does not have SD card slot")

    await ensure_sdcard(ensure_filesystem=False)

    if msg.operation == SdCardBackupManageOperationType.CHECK:
        print("sd_backup_manage: calling _check_health")
        return await _check_health()
    elif msg.operation == SdCardBackupManageOperationType.REFRESH:
        return await _refresh()
    elif msg.operation == SdCardBackupManageOperationType.WIPE:
        return await _wipe()
    elif msg.operation == SdCardBackupManageOperationType.COPY:
        return await _copy()
    else:
        raise ProcessError("Unknown operation")


async def _check_health() -> SdCardBackupHealth:
    from storage.device import get_backup_type, get_mnemonic_secret
    from storage.sd_seed_backup import check_health_of_backup_sdcard
    from trezor.enums import BackupType

    print("_check_health: start")

    await confirm_action(
        "confirm_sd_backup_check",
        "Check backup card",
        action="Check action",
        description="Checks health of the backup card.",
    )

    return check_health_of_backup_sdcard(
        get_mnemonic_secret() if get_backup_type() == BackupType.Bip39 else None
    )


async def _refresh() -> Success | Failure:
    from storage.device import get_backup_type, get_mnemonic_secret
    from trezor.ui.layouts.sdcard_eject import make_user_eject_sdcard
    from trezor.enums import BackupType
    from storage.sd_seed_backup import refresh_backup_sdcard

    await confirm_action(
        "confirm_sd_backup_refresh",
        "Refresh backup card",
        action="Refresh action",
        description="Refreshes backup card.",
        verb="REFRESH",
        hold=True,
        hold_danger=True,
    )
    success = refresh_backup_sdcard(
        get_mnemonic_secret() if get_backup_type() == BackupType.Bip39 else None
    )

    await make_user_eject_sdcard()
    return (
        Success("SD backup card refreshed.")
        if success
        else Failure("SD backup card refresh failed.")
    )


async def _wipe() -> Success:
    from storage.sd_seed_backup import wipe_backup_sdcard

    await confirm_action(
        "confirm_sd_backup_wipe",
        "Wipe backup card",
        action="Wipe action",
        description="Erase backup card. This action is irreversible.",
        verb="WIPE",
        hold=True,
        hold_danger=True,
    )

    wipe_backup_sdcard()
    return Success("SD backup card wiped.")


async def _copy() -> Success | Failure:
    from storage.sd_seed_backup import store_seed_on_sdcard, recover_seed_from_sdcard
    from trezor.ui.layouts.sdcard_eject import make_user_eject_sdcard
    from trezor.ui.layouts import show_warning
    from apps.common.sdcard import get_serial_num

    # TODO do we allow copying sd cards with seed different than the one stored on the device?
    await confirm_action(
        "confirm_sd_backup_copy",
        "Copy backup card",
        action="Do you really want to copy the backup SD card?",
    )

    read_mnemonic, read_backup_type = recover_seed_from_sdcard()
    if read_mnemonic is None or read_backup_type is None:
        return Failure("SD backup card copy failed.")
    sn = get_serial_num()
    await make_user_eject_sdcard()

    while True:
        await ensure_sdcard(ensure_filesystem=False)
        new_sn = get_serial_num()
        if new_sn == sn:
            await show_warning(
                "warning_sd_backup_same_card", "Insert a different card."
            )
        elif new_sn == 0:
            return Failure("SD backup card copy failed.")
        else:
            break

    # NOTE: should we delegate `mkfs` to `store_seed_on_sdcard` ?
    # TODO: code repetition with reset_device/__init__.py: sdcard_backup_seed(...)
    await ensure_sdcard(ensure_filesystem=True, for_sd_backup=True)
    store_seed_on_sdcard(read_mnemonic, read_backup_type)
    await make_user_eject_sdcard()
    return Success("SD card backup copy succeeded")
