from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import RecoveryDevice
    from trezor.wire import Context
    from trezor.messages import Success

# List of RecoveryDevice fields that can be set when doing dry-run recovery.
# All except `dry_run` are allowed for T1 compatibility, but their values are ignored.
# If set, `enforce_wordlist` must be True, because we do not support non-enforcing.
DRY_RUN_ALLOWED_FIELDS = ("dry_run", "word_count", "enforce_wordlist", "type")


async def recovery_device(ctx: Context, msg: RecoveryDevice) -> Success:
    """
    Recover BIP39/SLIP39 seed into empty device.
    Recovery is also possible with replugged Trezor. We call this process Persistence.
    User starts the process here using the RecoveryDevice msg and then they can unplug
    the device anytime and continue without a computer.
    """
    import storage
    import storage.device as storage_device
    import storage.recovery as storage_recovery
    from trezor import config, wire, workflow
    from trezor.enums import ButtonRequestType
    from trezor.ui.layouts import confirm_action, confirm_reset_device
    from apps.common.request_pin import (
        error_pin_invalid,
        request_pin_and_sd_salt,
        request_pin_confirm,
    )
    from .homescreen import recovery_homescreen, recovery_process

    dry_run = msg.dry_run  # local_cache_attribute

    # --------------------------------------------------------
    # validate
    if not dry_run and storage_device.is_initialized():
        raise wire.UnexpectedMessage("Already initialized")
    if dry_run and not storage_device.is_initialized():
        raise wire.NotInitialized("Device is not initialized")
    if msg.enforce_wordlist is False:
        raise wire.ProcessError(
            "Value enforce_wordlist must be True, Trezor Core enforces words automatically."
        )
    if dry_run:
        # check that only allowed fields are set
        for key, value in msg.__dict__.items():
            if key not in DRY_RUN_ALLOWED_FIELDS and value is not None:
                raise wire.ProcessError(f"Forbidden field set in dry-run: {key}")
    # END validate
    # --------------------------------------------------------

    if storage_recovery.is_in_progress():
        return await recovery_process(ctx)

    # --------------------------------------------------------
    # _continue_dialog
    if not dry_run:
        await confirm_reset_device(ctx, "Wallet recovery", recovery=True)
    else:
        await confirm_action(
            ctx,
            "confirm_seedcheck",
            "Seed check",
            description="Do you really want to check the recovery seed?",
            br_code=ButtonRequestType.ProtectCall,
        )
    # END _continue_dialog
    # --------------------------------------------------------

    if not dry_run:
        # wipe storage to make sure the device is in a clear state
        storage.reset()

    # for dry run pin needs to be entered
    if dry_run:
        curpin, salt = await request_pin_and_sd_salt(ctx, "Enter PIN")
        if not config.check_pin(curpin, salt):
            await error_pin_invalid(ctx)

    if not dry_run:
        # set up pin if requested
        if msg.pin_protection:
            newpin = await request_pin_confirm(ctx, allow_cancel=False)
            config.change_pin("", newpin, None, None)

        storage_device.set_passphrase_enabled(bool(msg.passphrase_protection))
        if msg.u2f_counter is not None:
            storage_device.set_u2f_counter(msg.u2f_counter)
        if msg.label is not None:
            storage_device.set_label(msg.label)

    storage_recovery.set_in_progress(True)
    storage_recovery.set_dry_run(bool(dry_run))

    workflow.set_default(recovery_homescreen)
    return await recovery_process(ctx)
