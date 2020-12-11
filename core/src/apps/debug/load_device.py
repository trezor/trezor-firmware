import storage
import storage.device
from trezor import config, wire
from trezor.crypto import bip39, slip39
from trezor.messages import BackupType
from trezor.messages.Success import Success
from trezor.pin import pin_to_int
from trezor.ui.components.tt.text import Text

from apps.common.confirm import require_confirm
from apps.management import backup_types


async def load_device(ctx, msg):
    word_count = _validate(msg)
    is_slip39 = backup_types.is_slip39_word_count(word_count)

    if not is_slip39 and not msg.skip_checksum and not bip39.check(msg.mnemonics[0]):
        raise wire.ProcessError("Mnemonic is not valid")

    await _warn(ctx)

    if not is_slip39:  # BIP-39
        secret = msg.mnemonics[0].encode()
        backup_type = BackupType.Bip39
    else:
        identifier, iteration_exponent, secret = slip39.recover_ems(msg.mnemonics)

        # this must succeed if the recover_ems call succeeded
        share = slip39.decode_mnemonic(msg.mnemonics[0])
        if share.group_count == 1:
            backup_type = BackupType.Slip39_Basic
        elif share.group_count > 1:
            backup_type = BackupType.Slip39_Advanced
        else:
            raise wire.ProcessError("Invalid group count")

        storage.device.set_slip39_identifier(identifier)
        storage.device.set_slip39_iteration_exponent(iteration_exponent)

    storage.device.store_mnemonic_secret(
        secret,
        backup_type,
        needs_backup=msg.needs_backup is True,
        no_backup=msg.no_backup is True,
    )
    storage.device.set_passphrase_enabled(msg.passphrase_protection)
    storage.device.set_label(msg.label or "")
    if msg.pin:
        config.change_pin(pin_to_int(""), pin_to_int(msg.pin), None, None)

    return Success(message="Device loaded")


def _validate(msg) -> int:
    if storage.device.is_initialized():
        raise wire.UnexpectedMessage("Already initialized")

    if not msg.mnemonics:
        raise wire.ProcessError("No mnemonic provided")

    word_count = len(msg.mnemonics[0].split(" "))
    for m in msg.mnemonics[1:]:
        if word_count != len(m.split(" ")):
            raise wire.ProcessError(
                "All shares are required to have the same number of words"
            )

    return word_count


async def _warn(ctx: wire.Context):
    text = Text("Loading seed")
    text.bold("Loading private seed", "is not recommended.")
    text.normal("Continue only if you", "know what you are doing!")
    await require_confirm(ctx, text)
