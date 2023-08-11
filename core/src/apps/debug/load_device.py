from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import LoadDevice, Success


async def load_device(msg: LoadDevice) -> Success:
    import storage.device as storage_device
    from trezor import TR, config
    from trezor.crypto import bip39, slip39
    from trezor.enums import BackupType
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_action
    from trezor.wire import ProcessError, UnexpectedMessage

    from apps.management import backup_types

    mnemonics = msg.mnemonics  # local_cache_attribute

    # _validate
    if storage_device.is_initialized():
        raise UnexpectedMessage("Already initialized")
    if not mnemonics:
        raise ProcessError("No mnemonic provided")

    word_count = len(msg.mnemonics[0].split(" "))
    for m in mnemonics[1:]:
        if word_count != len(m.split(" ")):
            raise ProcessError(
                "All shares are required to have the same number of words"
            )
    # END _validate

    is_slip39 = backup_types.is_slip39_word_count(word_count)

    if not is_slip39 and not msg.skip_checksum and not bip39.check(mnemonics[0]):
        raise ProcessError("Mnemonic is not valid")

    # _warn
    await confirm_action(
        "warn_loading_seed",
        TR.debug__loading_seed,
        TR.debug__loading_seed_not_recommended,
        TR.words__know_what_your_doing,
    )
    # END _warn

    if not is_slip39:  # BIP-39
        secret = msg.mnemonics[0].encode()
        backup_type = BackupType.Bip39
    else:
        identifier, iteration_exponent, secret = slip39.recover_ems(mnemonics)

        # this must succeed if the recover_ems call succeeded
        share = slip39.decode_mnemonic(mnemonics[0])
        if share.group_count == 1:
            backup_type = BackupType.Slip39_Basic
        elif share.group_count > 1:
            backup_type = BackupType.Slip39_Advanced
        else:
            raise ProcessError("Invalid group count")

        storage_device.set_slip39_identifier(identifier)
        storage_device.set_slip39_iteration_exponent(iteration_exponent)

    storage_device.store_mnemonic_secret(
        secret,
        backup_type,
        needs_backup=msg.needs_backup is True,
        no_backup=msg.no_backup is True,
    )
    storage_device.set_passphrase_enabled(bool(msg.passphrase_protection))
    storage_device.set_label(msg.label or "")
    if msg.pin:
        config.change_pin("", msg.pin, None, None)

    return Success(message="Device loaded")
