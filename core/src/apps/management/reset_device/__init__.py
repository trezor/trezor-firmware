from typing import TYPE_CHECKING, Sequence

import storage
import storage.device as storage_device
from trezor import TR
from trezor.crypto import hmac, slip39
from trezor.enums import BackupType, MessageType
from trezor.ui.layouts import confirm_action
from trezor.wire import ProcessError

from apps.common import backup_types

from . import layout

if __debug__:
    import storage.debug

if TYPE_CHECKING:
    from trezor.messages import ResetDevice, Success


BAK_T_BIP39 = BackupType.Bip39  # global_import_cache
BAK_T_SLIP39_BASIC = BackupType.Slip39_Basic  # global_import_cache
BAK_T_SLIP39_ADVANCED = BackupType.Slip39_Advanced  # global_import_cache
BAK_T_SLIP39_SINGLE_EXT = BackupType.Slip39_Single_Extendable  # global_import_cache
BAK_T_SLIP39_BASIC_EXT = BackupType.Slip39_Basic_Extendable  # global_import_cache
BAK_T_SLIP39_ADVANCED_EXT = BackupType.Slip39_Advanced_Extendable  # global_import_cache
_DEFAULT_BACKUP_TYPE = BAK_T_BIP39


async def reset_device(msg: ResetDevice) -> Success:
    from trezor import config
    from trezor.crypto import bip39, random
    from trezor.messages import EntropyAck, EntropyRequest, Success
    from trezor.pin import render_empty_loader
    from trezor.ui.layouts import (
        confirm_reset_device,
        prompt_backup,
        show_wallet_created_success,
    )
    from trezor.wire.context import call

    from apps.common.request_pin import request_pin_confirm

    backup_type = msg.backup_type  # local_cache_attribute

    # Force extendable backup.
    if backup_type == BAK_T_SLIP39_BASIC:
        backup_type = BAK_T_SLIP39_BASIC_EXT

    if backup_type == BAK_T_SLIP39_ADVANCED:
        backup_type = BAK_T_SLIP39_ADVANCED_EXT

    # validate parameters and device state
    _validate_reset_device(msg)

    # make sure user knows they're setting up a new wallet
    await confirm_reset_device()

    # Rendering empty loader so users do not feel a freezing screen
    render_empty_loader(config.StorageMessage.PROCESSING_MSG)

    # wipe storage to make sure the device is in a clear state
    storage.reset()

    # Check backup type, perform type-specific handling
    if backup_types.is_slip39_backup_type(backup_type):
        # set SLIP39 parameters
        storage_device.set_slip39_iteration_exponent(slip39.DEFAULT_ITERATION_EXPONENT)
    elif backup_type != BAK_T_BIP39:
        # Unknown backup type.
        raise RuntimeError

    storage_device.set_backup_type(backup_type)

    # request and set new PIN
    if msg.pin_protection:
        newpin = await request_pin_confirm()
        if not config.change_pin("", newpin, None, None):
            raise ProcessError("Failed to set PIN")

    prev_int_entropy = None
    while True:
        # generate internal entropy
        int_entropy = random.bytes(32, True)
        if __debug__:
            storage.debug.reset_internal_entropy[:] = int_entropy

        entropy_commitment = (
            hmac(hmac.SHA256, int_entropy, b"").digest() if msg.entropy_check else None
        )

        # request external entropy and compute the master secret
        entropy_ack = await call(
            EntropyRequest(
                entropy_commitment=entropy_commitment, prev_entropy=prev_int_entropy
            ),
            EntropyAck,
        )
        ext_entropy = entropy_ack.entropy
        # For SLIP-39 this is the Encrypted Master Secret
        secret = _compute_secret_from_entropy(int_entropy, ext_entropy, msg.strength)

        if backup_type == BAK_T_BIP39:
            # in BIP-39 we store mnemonic string instead of the secret
            secret = bip39.from_data(secret).encode()

        if not msg.entropy_check or await _entropy_check(secret):
            break

        prev_int_entropy = int_entropy

    # If either of skip_backup or no_backup is specified, we are not doing backup now.
    # Otherwise, we try to do it.
    perform_backup = not msg.no_backup and not msg.skip_backup

    # Wallet created successfully
    await show_wallet_created_success()

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
        needs_backup=not perform_backup,
        no_backup=bool(msg.no_backup),
    )

    # if we backed up the wallet, show success message
    if perform_backup:
        await layout.show_backup_success()

    return Success(message="Initialized")


async def _entropy_check(secret: bytes) -> bool:
    """Returns True to indicate that entropy check loop should end."""
    from trezor.messages import EntropyCheckContinue, EntropyCheckReady, GetPublicKey
    from trezor.wire.context import call_any

    from apps.bitcoin.get_public_key import get_public_key
    from apps.common import coininfo, paths
    from apps.common.keychain import Keychain
    from apps.common.mnemonic import get_seed

    seed = get_seed(mnemonic_secret=secret)

    msg = EntropyCheckReady()
    while True:
        req = await call_any(
            msg,
            MessageType.EntropyCheckContinue,
            MessageType.GetPublicKey,
        )
        assert req.MESSAGE_WIRE_TYPE is not None

        if EntropyCheckContinue.is_type_of(req):
            return req.finish

        assert GetPublicKey.is_type_of(req)
        req.show_display = False
        curve_name = req.ecdsa_curve_name or coininfo.by_name(req.coin_name).curve_name
        keychain = Keychain(seed, curve_name, [paths.AlwaysMatchingSchema])
        msg = await get_public_key(req, keychain=keychain)


async def _backup_bip39(mnemonic: str) -> None:
    words = mnemonic.split()
    await layout.show_backup_intro(single_share=True, num_of_words=len(words))
    await layout.show_and_confirm_single_share(words)


async def _backup_slip39_single(
    encrypted_master_secret: bytes, extendable: bool
) -> None:
    mnemonics = _get_slip39_mnemonics(encrypted_master_secret, 1, ((1, 1),), extendable)
    words = mnemonics[0][0].split()

    # for a single 1-of-1 group, we use the same layouts as for BIP39
    await layout.show_backup_intro(single_share=True, num_of_words=len(words))
    await layout.show_and_confirm_single_share(words)


async def _backup_slip39_basic(
    encrypted_master_secret: bytes, num_of_words: int, extendable: bool
) -> None:
    group_threshold = 1

    await layout.show_backup_intro(single_share=False)

    # get number of shares
    await layout.slip39_show_checklist(0, advanced=False)
    share_count = await layout.slip39_prompt_number_of_shares(num_of_words)

    # get threshold
    await layout.slip39_show_checklist(1, advanced=False, count=share_count)
    share_threshold = await layout.slip39_prompt_threshold(share_count)

    mnemonics = _get_slip39_mnemonics(
        encrypted_master_secret,
        group_threshold,
        ((share_threshold, share_count),),
        extendable,
    )

    # show and confirm individual shares
    await layout.slip39_show_checklist(
        2, advanced=False, count=share_count, threshold=share_threshold
    )
    await layout.slip39_basic_show_and_confirm_shares(mnemonics[0])


async def _backup_slip39_advanced(
    encrypted_master_secret: bytes, num_of_words: int, extendable: bool
) -> None:
    await layout.show_backup_intro(single_share=False)

    # get number of groups
    await layout.slip39_show_checklist(0, advanced=True)
    groups_count = await layout.slip39_advanced_prompt_number_of_groups()

    # get group threshold
    await layout.slip39_show_checklist(1, advanced=True, count=groups_count)
    group_threshold = await layout.slip39_advanced_prompt_group_threshold(groups_count)

    # get shares and thresholds
    await layout.slip39_show_checklist(
        2, advanced=True, count=groups_count, threshold=group_threshold
    )
    groups = []
    for i in range(groups_count):
        share_count = await layout.slip39_prompt_number_of_shares(num_of_words, i)
        share_threshold = await layout.slip39_prompt_threshold(share_count, i)
        groups.append((share_threshold, share_count))

    mnemonics = _get_slip39_mnemonics(
        encrypted_master_secret, group_threshold, groups, extendable
    )

    # show and confirm individual shares
    await layout.slip39_advanced_show_and_confirm_shares(mnemonics)


async def backup_slip39_custom(
    encrypted_master_secret: bytes,
    group_threshold: int,
    groups: Sequence[tuple[int, int]],
    extendable: bool,
) -> None:
    # show and confirm individual shares
    if len(groups) == 1 and groups[0][0] == 1 and groups[0][1] == 1:
        await _backup_slip39_single(encrypted_master_secret, extendable)
    else:
        mnemonics = _get_slip39_mnemonics(
            encrypted_master_secret, group_threshold, groups, extendable
        )
        await confirm_action(
            "warning_shamir_backup",
            TR.reset__title_shamir_backup,
            description=TR.reset__create_x_of_y_multi_share_backup_template.format(
                groups[0][0], groups[0][1]
            ),
            verb=TR.buttons__continue,
        )
        if len(groups) == 1:
            await layout.slip39_basic_show_and_confirm_shares(mnemonics[0])
        else:
            await layout.slip39_advanced_show_and_confirm_shares(mnemonics)


def _get_slip39_mnemonics(
    encrypted_master_secret: bytes,
    group_threshold: int,
    groups: Sequence[tuple[int, int]],
    extendable: bool,
) -> list[list[str]]:
    if extendable:
        identifier = slip39.generate_random_identifier()
    else:
        identifier = storage_device.get_slip39_identifier()

    iteration_exponent = storage_device.get_slip39_iteration_exponent()
    if identifier is None or iteration_exponent is None:
        raise ValueError

    # generate the mnemonics
    return slip39.split_ems(
        group_threshold,
        groups,
        identifier,
        extendable,
        iteration_exponent,
        encrypted_master_secret,
    )


def _validate_reset_device(msg: ResetDevice) -> None:
    from trezor.wire import UnexpectedMessage

    backup_type = msg.backup_type or _DEFAULT_BACKUP_TYPE
    if backup_types.is_slip39_backup_type(backup_type):
        if msg.strength not in (128, 256):
            raise ProcessError("Invalid strength (has to be 128 or 256 bits)")
    elif backup_type == BAK_T_BIP39:
        if msg.strength not in (128, 192, 256):
            raise ProcessError("Invalid strength (has to be 128, 192 or 256 bits)")
    else:
        raise ProcessError("Backup type not implemented")

    if storage_device.is_initialized():
        raise UnexpectedMessage("Already initialized")


def _compute_secret_from_entropy(
    int_entropy: bytes, ext_entropy: bytes, strength_bits: int
) -> bytes:
    from trezor.crypto import hashlib

    # combine internal and external entropy
    ehash = hashlib.sha256()
    ehash.update(int_entropy)
    ehash.update(ext_entropy)
    entropy = ehash.digest()
    # take a required number of bytes
    strength = strength_bits // 8
    secret = entropy[:strength]
    return secret


async def backup_seed(backup_type: BackupType, mnemonic_secret: bytes) -> None:
    if backup_types.is_slip39_backup_type(backup_type):
        num_of_words = backup_types.get_num_of_words_per_share(
            backup_type, len(mnemonic_secret)
        )
        extendable = backup_types.is_extendable_backup_type(backup_type)
        if backup_types.is_slip39_advanced_backup_type(backup_type):
            await _backup_slip39_advanced(mnemonic_secret, num_of_words, extendable)
        elif backup_type == BAK_T_SLIP39_SINGLE_EXT:
            await _backup_slip39_single(mnemonic_secret, extendable)
        else:
            await _backup_slip39_basic(mnemonic_secret, num_of_words, extendable)
    else:
        await _backup_bip39(mnemonic_secret.decode())
