from typing import TYPE_CHECKING

from trezor.enums import RecoveryKind

if TYPE_CHECKING:
    from trezor.messages import RecoveryDevice, Success

# List of RecoveryDevice fields that can be set when doing dry-run recovery.
# All except `kind` are allowed for T1 compatibility, but their values are ignored.
# If set, `enforce_wordlist` must be True, because we do not support non-enforcing.
DRY_RUN_ALLOWED_FIELDS = ("kind", "word_count", "enforce_wordlist", "type")


async def recovery_device(msg: RecoveryDevice) -> Success:
    """
    Recover BIP39/SLIP39 seed into empty device.
    Recovery is also possible with replugged Trezor. We call this process Persistence.
    User starts the process here using the RecoveryDevice msg and then they can unplug
    the device anytime and continue without a computer.
    """
    import storage
    import storage.device as storage_device
    import storage.recovery as storage_recovery
    from trezor import TR, config, wire, workflow
    from trezor.enums import BackupType, ButtonRequestType
    from trezor.ui.layouts import confirm_action, confirm_reset_device

    from apps.common import mnemonic
    from apps.common.request_pin import (
        error_pin_invalid,
        request_pin_and_sd_salt,
        request_pin_confirm,
    )

    from .homescreen import recovery_homescreen, recovery_process

    recovery_kind = msg.kind  # local_cache_attribute

    # --------------------------------------------------------
    # validate
    if recovery_kind == RecoveryKind.NormalRecovery:
        if storage_device.is_initialized():
            raise wire.UnexpectedMessage("Already initialized")
    elif recovery_kind in (RecoveryKind.DryRun, RecoveryKind.UnlockRepeatedBackup):
        if not storage_device.is_initialized():
            raise wire.NotInitialized("Device is not initialized")
        if (
            recovery_kind == RecoveryKind.UnlockRepeatedBackup
            and mnemonic.get_type() == BackupType.Bip39
        ):
            raise wire.ProcessError("Repeated Backup not available for BIP39 backups")
        # check that only allowed fields are set
        for key, value in msg.__dict__.items():
            if key not in DRY_RUN_ALLOWED_FIELDS and value is not None:
                raise wire.ProcessError(f"Forbidden field set in dry-run: {key}")
    else:
        raise RuntimeError  # Unknown RecoveryKind

    if msg.enforce_wordlist is False:
        raise wire.ProcessError(
            "Value enforce_wordlist must be True, Trezor Core enforces words automatically."
        )
    # END validate
    # --------------------------------------------------------

    if storage_recovery.is_in_progress():
        return await recovery_process()

    if recovery_kind == RecoveryKind.NormalRecovery:
        await confirm_reset_device(TR.recovery__title_recover, recovery=True)

        # wipe storage to make sure the device is in a clear state
        storage.reset()

        # set up pin if requested
        if msg.pin_protection:
            newpin = await request_pin_confirm(allow_cancel=False)
            config.change_pin("", newpin, None, None)

        storage_device.set_passphrase_enabled(bool(msg.passphrase_protection))

        if msg.u2f_counter is not None:
            storage_device.set_u2f_counter(msg.u2f_counter)

        if msg.label is not None:
            storage_device.set_label(msg.label)

    elif recovery_kind in (RecoveryKind.DryRun, RecoveryKind.UnlockRepeatedBackup):
        title = (
            TR.recovery__title_dry_run
            if recovery_kind == RecoveryKind.DryRun
            else TR.recovery__title_unlock_repeated_backup
        )
        await confirm_action(
            "confirm_seedcheck",
            title,
            description=TR.recovery__check_dry_run,
            br_code=ButtonRequestType.ProtectCall,
            verb=TR.buttons__check,
        )

        curpin, salt = await request_pin_and_sd_salt(TR.pin__enter)
        if not config.check_pin(curpin, salt):
            await error_pin_invalid()

    storage_recovery.set_in_progress(True)

    storage_recovery.set_kind(int(recovery_kind))

    workflow.set_default(recovery_homescreen)

    return await recovery_process()
