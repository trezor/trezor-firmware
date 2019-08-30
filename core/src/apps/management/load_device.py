from trezor import config, wire
from trezor.crypto import bip39, slip39
from trezor.messages import BackupType
from trezor.messages.Success import Success
from trezor.pin import pin_to_int
from trezor.ui.text import Text

from apps.common import storage
from apps.common.confirm import require_confirm
from apps.management.recovery_device import backup_types


async def load_device(ctx, msg):
    if storage.is_initialized():
        raise wire.UnexpectedMessage("Already initialized")

    if msg.node is not None:
        raise wire.ProcessError("LoadDevice.node is not supported")

    if not msg.mnemonics:
        raise wire.ProcessError("No mnemonic provided")

    word_count = len(msg.mnemonics[0].split(" "))
    for m in msg.mnemonics[1:]:
        if word_count != len(m.split(" ")):
            raise wire.ProcessError(
                "All shares are required to have the same number of words"
            )

    possible_backup_types = backup_types.get(word_count)

    if (
        BackupType.Bip39 in possible_backup_types
        and not msg.skip_checksum
        and not bip39.check(msg.mnemonics[0])
    ):
        raise wire.ProcessError("Mnemonic is not valid")

    text = Text("Loading seed")
    text.bold("Loading private seed", "is not recommended.")
    text.normal("Continue only if you", "know what you are doing!")
    await require_confirm(ctx, text)

    if BackupType.Bip39 in possible_backup_types:
        secret = msg.mnemonics[0].encode()
    elif backup_types.is_slip39(possible_backup_types):
        identifier, iteration_exponent, secret = slip39.combine_mnemonics(msg.mnemonics)
        possible_backup_types = [BackupType.Slip39_Basic]  # TODO!!!
        storage.device.set_slip39_identifier(identifier)
        storage.device.set_slip39_iteration_exponent(iteration_exponent)
    else:
        raise RuntimeError("Unknown mnemonic type")

    if len(possible_backup_types) != 1:
        # Only one possible backup type should be left before storing into the storage.
        raise RuntimeError
    storage.device.store_mnemonic_secret(
        secret, possible_backup_types[0], needs_backup=True, no_backup=False
    )
    storage.device.load_settings(
        use_passphrase=msg.passphrase_protection, label=msg.label
    )
    if msg.pin:
        config.change_pin(pin_to_int(""), pin_to_int(msg.pin))

    return Success(message="Device loaded")
