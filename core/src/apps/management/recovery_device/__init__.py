from trezor import config, ui, wire
from trezor.messages import ButtonRequestType
from trezor.messages.Success import Success
from trezor.pin import pin_to_int
from trezor.ui.text import Text

from apps.common import storage
from apps.common.confirm import require_confirm
from apps.management.change_pin import request_pin_ack, request_pin_confirm
from apps.management.recovery_device.homescreen import recovery_process

if False:
    from trezor.messages.RecoveryDevice import RecoveryDevice


async def recovery_device(ctx: wire.Context, msg: RecoveryDevice) -> Success:
    """
    Recover BIP39/SLIP39 seed into empty device.
    Recovery is also possible with replugged Trezor. We call this process Persistance.
    User starts the process here using the RecoveryDevice msg and then they can unplug
    the device anytime and continue without a computer.
    """
    _check_state(msg)

    if not msg.dry_run:
        title = "Wallet recovery"
        text = Text(title, ui.ICON_RECOVERY)
        text.normal("Do you really want to", "recover the wallet?", "")
    else:
        title = "Seed check"
        text = Text(title, ui.ICON_RECOVERY)
        text.normal("Do you really want to", "check the recovery", "seed?")
    await require_confirm(ctx, text, code=ButtonRequestType.ProtectCall)

    # for dry run pin needs to entered
    if msg.dry_run:
        if config.has_pin():
            curpin = await request_pin_ack(ctx, "Enter PIN", config.get_pin_rem())
        else:
            curpin = ""
        if not config.check_pin(pin_to_int(curpin)):
            raise wire.PinInvalid("PIN invalid")

    # set up pin if requested
    if msg.pin_protection:
        if msg.dry_run:
            raise wire.ProcessError("Can't setup PIN during dry_run recovery.")
        newpin = await request_pin_confirm(ctx, allow_cancel=False)
        config.change_pin(pin_to_int(""), pin_to_int(newpin))

    storage.device.set_u2f_counter(msg.u2f_counter)
    storage.device.load_settings(
        label=msg.label, use_passphrase=msg.passphrase_protection
    )
    storage.recovery.set_in_progress(True)
    storage.recovery.set_dry_run(msg.dry_run)

    result = await recovery_process(ctx)

    return result


def _check_state(msg: RecoveryDevice):
    if not msg.dry_run and storage.is_initialized():
        raise wire.UnexpectedMessage("Already initialized")
    if msg.dry_run and not storage.is_initialized():
        raise wire.UnexpectedMessage("Device is not initialized")

    if storage.recovery.is_in_progress():
        raise RuntimeError(
            "Function recovery_device should not be invoked when recovery is already in progress"
        )

    if msg.enforce_wordlist is False:
        raise wire.ProcessError(
            "Value enforce_wordlist must be True, Trezor Core enforces words automatically."
        )
