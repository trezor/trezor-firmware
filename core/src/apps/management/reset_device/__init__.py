from typing import TYPE_CHECKING

import storage
import storage.device as storage_device
from trezor.crypto import slip39
from trezor.enums import BackupType
from trezor.wire import ProcessError

from . import layout

if __debug__:
    import storage.debug

if TYPE_CHECKING:
    from trezor.messages import ResetDevice, Success


BAK_T_BIP39 = BackupType.Bip39  # global_import_cache
BAK_T_SLIP39_BASIC = BackupType.Slip39_Basic  # global_import_cache
BAK_T_SLIP39_ADVANCED = BackupType.Slip39_Advanced  # global_import_cache
_DEFAULT_BACKUP_TYPE = BAK_T_BIP39


async def reset_device(msg: ResetDevice) -> Success:
    from trezor import TR, config
    from trezor.crypto import bip39, random
    from trezor.messages import EntropyAck, EntropyRequest, Success
    from trezor.pin import render_empty_loader
    from trezor.ui.layouts import confirm_reset_device, prompt_backup
    from trezor.wire.context import call

    from apps.common.request_pin import request_pin_confirm

    backup_type = msg.backup_type  # local_cache_attribute

    # validate parameters and device state
    _validate_reset_device(msg)

    # make sure user knows they're setting up a new wallet
    if backup_type in (BAK_T_SLIP39_BASIC, BAK_T_SLIP39_ADVANCED):
        title = TR.reset__title_create_wallet_shamir
    else:
        title = TR.reset__title_create_wallet
    await confirm_reset_device(title)

    # Rendering empty loader so users do not feel a freezing screen
    render_empty_loader(TR.progress__processing, "")

    # wipe storage to make sure the device is in a clear state
    storage.reset()

    # request and set new PIN
    if msg.pin_protection:
        newpin = await request_pin_confirm()
        if not config.change_pin("", newpin, None, None):
            raise ProcessError("Failed to set PIN")

    # generate and display internal entropy
    int_entropy = random.bytes(32, True)
    if __debug__:
        storage.debug.reset_internal_entropy = int_entropy
    if msg.display_random:
        await layout.show_internal_entropy(int_entropy)

    # request external entropy and compute the master secret
    entropy_ack = await call(EntropyRequest(), EntropyAck)
    ext_entropy = entropy_ack.entropy
    # For SLIP-39 this is the Encrypted Master Secret
    secret = _compute_secret_from_entropy(int_entropy, ext_entropy, msg.strength)

    # Check backup type, perform type-specific handling
    if backup_type == BAK_T_BIP39:
        # in BIP-39 we store mnemonic string instead of the secret
        secret = bip39.from_data(secret).encode()
    elif backup_type in (BAK_T_SLIP39_BASIC, BAK_T_SLIP39_ADVANCED):
        # generate and set SLIP39 parameters
        storage_device.set_slip39_identifier(slip39.generate_random_identifier())
        storage_device.set_slip39_iteration_exponent(slip39.DEFAULT_ITERATION_EXPONENT)
    else:
        # Unknown backup type.
        raise RuntimeError

    # If either of skip_backup or no_backup is specified, we are not doing backup now.
    # Otherwise, we try to do it.
    perform_backup = not msg.no_backup and not msg.skip_backup

    # If doing backup, ask the user to confirm.
    if perform_backup:
        perform_backup = await prompt_backup()

    # generate and display backup information for the master secret
    if perform_backup:
        await backup_seed(backup_type, secret)

    # write settings and master secret into storage
    if msg.label is not None:
        storage_device.set_label(msg.label)
    storage_device.set_passphrase_enabled(bool(msg.passphrase_protection))
    storage_device.store_mnemonic_secret(
        secret,  # for SLIP-39, this is the EMS
        backup_type,
        needs_backup=not perform_backup,
        no_backup=bool(msg.no_backup),
    )

    # if we backed up the wallet, show success message
    if perform_backup:
        await layout.show_backup_success()

    return Success(message="Initialized")


async def _backup_slip39_basic(encrypted_master_secret: bytes) -> None:
    # get number of shares
    await layout.slip39_show_checklist(0, BAK_T_SLIP39_BASIC)
    shares_count = await layout.slip39_prompt_number_of_shares()

    # get threshold
    await layout.slip39_show_checklist(1, BAK_T_SLIP39_BASIC)
    threshold = await layout.slip39_prompt_threshold(shares_count)

    identifier = storage_device.get_slip39_identifier()
    iteration_exponent = storage_device.get_slip39_iteration_exponent()
    if identifier is None or iteration_exponent is None:
        raise ValueError

    # generate the mnemonics
    mnemonics = slip39.split_ems(
        1,  # Single Group threshold
        [(threshold, shares_count)],  # Single Group threshold/count
        identifier,
        iteration_exponent,
        encrypted_master_secret,
    )[0]

    # show and confirm individual shares
    await layout.slip39_show_checklist(2, BAK_T_SLIP39_BASIC)
    await layout.slip39_basic_show_and_confirm_shares(mnemonics)


async def _backup_slip39_advanced(encrypted_master_secret: bytes) -> None:
    # get number of groups
    await layout.slip39_show_checklist(0, BAK_T_SLIP39_ADVANCED)
    groups_count = await layout.slip39_advanced_prompt_number_of_groups()

    # get group threshold
    await layout.slip39_show_checklist(1, BAK_T_SLIP39_ADVANCED)
    group_threshold = await layout.slip39_advanced_prompt_group_threshold(groups_count)

    # get shares and thresholds
    await layout.slip39_show_checklist(2, BAK_T_SLIP39_ADVANCED)
    groups = []
    for i in range(groups_count):
        share_count = await layout.slip39_prompt_number_of_shares(i)
        share_threshold = await layout.slip39_prompt_threshold(share_count, i)
        groups.append((share_threshold, share_count))

    identifier = storage_device.get_slip39_identifier()
    iteration_exponent = storage_device.get_slip39_iteration_exponent()
    if identifier is None or iteration_exponent is None:
        raise ValueError

    # generate the mnemonics
    mnemonics = slip39.split_ems(
        group_threshold,
        groups,
        identifier,
        iteration_exponent,
        encrypted_master_secret,
    )

    # show and confirm individual shares
    await layout.slip39_advanced_show_and_confirm_shares(mnemonics)


def _validate_reset_device(msg: ResetDevice) -> None:
    from trezor.wire import UnexpectedMessage

    from .. import backup_types

    backup_type = msg.backup_type or _DEFAULT_BACKUP_TYPE
    if backup_type not in (
        BAK_T_BIP39,
        BAK_T_SLIP39_BASIC,
        BAK_T_SLIP39_ADVANCED,
    ):
        raise ProcessError("Backup type not implemented.")
    if backup_types.is_slip39_backup_type(backup_type):
        if msg.strength not in (128, 256):
            raise ProcessError("Invalid strength (has to be 128 or 256 bits)")
    else:  # BIP-39
        if msg.strength not in (128, 192, 256):
            raise ProcessError("Invalid strength (has to be 128, 192 or 256 bits)")
    if msg.display_random and (msg.skip_backup or msg.no_backup):
        raise ProcessError("Can't show internal entropy when backup is skipped")
    if storage_device.is_initialized():
        raise UnexpectedMessage("Already initialized")


def _compute_secret_from_entropy(
    int_entropy: bytes, ext_entropy: bytes, strength_in_bytes: int
) -> bytes:
    from trezor.crypto import hashlib

    # combine internal and external entropy
    ehash = hashlib.sha256()
    ehash.update(int_entropy)
    ehash.update(ext_entropy)
    entropy = ehash.digest()
    # take a required number of bytes
    strength = strength_in_bytes // 8
    secret = entropy[:strength]
    return secret


async def backup_seed(backup_type: BackupType, mnemonic_secret: bytes) -> None:
    if backup_type == BAK_T_SLIP39_BASIC:
        await _backup_slip39_basic(mnemonic_secret)
    elif backup_type == BAK_T_SLIP39_ADVANCED:
        await _backup_slip39_advanced(mnemonic_secret)
    else:
        await layout.bip39_show_and_confirm_mnemonic(mnemonic_secret.decode())
