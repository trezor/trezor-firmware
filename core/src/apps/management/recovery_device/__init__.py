import storage
import storage.device
import storage.recovery
from trezor import config, ui, wire, workflow
from trezor.enums import ButtonRequestType
from trezor.messages import Success
from trezor.ui.components.tt.text import Text

from apps.common.confirm import require_confirm
from apps.common.request_pin import (
    error_pin_invalid,
    request_pin_and_sd_salt,
    request_pin_confirm,
)

from .homescreen import recovery_homescreen, recovery_process

if False:
    from trezor.messages import RecoveryDevice


# List of RecoveryDevice fields that can be set when doing dry-run recovery.
# All except `dry_run` are allowed for T1 compatibility, but their values are ignored.
# If set, `enforce_wordlist` must be True, because we do not support non-enforcing.
DRY_RUN_ALLOWED_FIELDS = ("dry_run", "word_count", "enforce_wordlist", "type")


async def recovery_device(ctx: wire.Context, msg: RecoveryDevice) -> Success:
    """
    Recover BIP39/SLIP39 seed into empty device.
    Recovery is also possible with replugged Trezor. We call this process Persistance.
    User starts the process here using the RecoveryDevice msg and then they can unplug
    the device anytime and continue without a computer.
    """
    _validate(msg)

    if storage.recovery.is_in_progress():
        return await recovery_process(ctx)

    await _continue_dialog(ctx, msg)

    if not msg.dry_run:
        # wipe storage to make sure the device is in a clear state
        storage.reset()

    # for dry run pin needs to be entered
    if msg.dry_run:
        curpin, salt = await request_pin_and_sd_salt(ctx, "Enter PIN")
        if not config.check_pin(curpin, salt):
            await error_pin_invalid(ctx)

    if not msg.dry_run:
        # set up pin if requested
        if msg.pin_protection:
            newpin = await request_pin_confirm(ctx, allow_cancel=False)
            config.change_pin("", newpin, None, None)

        storage.device.set_passphrase_enabled(bool(msg.passphrase_protection))
        if msg.u2f_counter is not None:
            storage.device.set_u2f_counter(msg.u2f_counter)
        if msg.label is not None:
            storage.device.set_label(msg.label)

    storage.recovery.set_in_progress(True)
    storage.recovery.set_dry_run(bool(msg.dry_run))

    workflow.set_default(recovery_homescreen)
    return await recovery_process(ctx)


def _validate(msg: RecoveryDevice) -> None:
    if not msg.dry_run and storage.device.is_initialized():
        raise wire.UnexpectedMessage("Already initialized")
    if msg.dry_run and not storage.device.is_initialized():
        raise wire.NotInitialized("Device is not initialized")

    if msg.enforce_wordlist is False:
        raise wire.ProcessError(
            "Value enforce_wordlist must be True, Trezor Core enforces words automatically."
        )

    if msg.dry_run:
        # check that only allowed fields are set
        for key, value in msg.__dict__.items():
            if key not in DRY_RUN_ALLOWED_FIELDS and value is not None:
                raise wire.ProcessError(
                    "Forbidden field set in dry-run: {}".format(key)
                )


async def _continue_dialog(ctx: wire.Context, msg: RecoveryDevice) -> None:
    if not msg.dry_run:
        text = Text("Recovery mode", ui.ICON_RECOVERY, new_lines=False)
        text.bold("Do you really want to recover a wallet?")
        text.br()
        text.br_half()
        text.normal("By continuing you agree")
        text.br()
        text.normal("to ")
        text.bold("https://trezor.io/tos")
    else:
        text = Text("Seed check", ui.ICON_RECOVERY, new_lines=False)
        text.normal("Do you really want to check the recovery seed?")
    await require_confirm(ctx, text, code=ButtonRequestType.ProtectCall)
