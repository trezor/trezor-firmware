from trezor import config, wire
from trezor.crypto import bip39, slip39
from trezor.messages.Success import Success
from trezor.pin import pin_to_int
from trezor.ui.text import Text

from apps.common import mnemonic, storage
from apps.common.confirm import require_confirm


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

    mnemonic_type = mnemonic.type_from_word_count(word_count)

    if (
        mnemonic_type == mnemonic.TYPE_BIP39
        and not msg.skip_checksum
        and not bip39.check(msg.mnemonics[0])
    ):
        raise wire.ProcessError("Mnemonic is not valid")

    text = Text("Loading seed")
    text.bold("Loading private seed", "is not recommended.")
    text.normal("Continue only if you", "know what you are doing!")
    await require_confirm(ctx, text)

    if mnemonic_type == mnemonic.TYPE_BIP39:
        secret = msg.mnemonics[0].encode()
    elif mnemonic_type == mnemonic.TYPE_SLIP39:
        identifier, iteration_exponent, secret = slip39.combine_mnemonics(msg.mnemonics)
        storage.device.set_slip39_identifier(identifier)
        storage.device.set_slip39_iteration_exponent(iteration_exponent)
    else:
        raise RuntimeError("Unknown mnemonic type")

    storage.device.store_mnemonic_secret(
        secret, mnemonic_type, needs_backup=True, no_backup=False
    )
    storage.device.load_settings(
        use_passphrase=msg.passphrase_protection, label=msg.label
    )
    if msg.pin:
        config.change_pin(pin_to_int(""), pin_to_int(msg.pin), None, None)

    return Success(message="Device loaded")
