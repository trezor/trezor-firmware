import storage
import storage.device
from trezor import config, wire
from trezor.crypto import bip39, hashlib, random, slip39
from trezor.messages import BackupType
from trezor.messages.EntropyAck import EntropyAck
from trezor.messages.EntropyRequest import EntropyRequest
from trezor.messages.Success import Success
from trezor.pin import pin_to_int
from trezor.ui.layouts import confirm_backup, confirm_reset_device, require
from trezor.ui.loader import LoadingAnimation

from .. import backup_types
from ..change_pin import request_pin_confirm
from . import layout

if __debug__:
    from apps import debug

if False:
    from trezor.messages.ResetDevice import ResetDevice

_DEFAULT_BACKUP_TYPE = BackupType.Bip39


async def reset_device(ctx: wire.Context, msg: ResetDevice) -> Success:
    # validate parameters and device state
    _validate_reset_device(msg)

    # make sure user knows they're setting up a new wallet
    if msg.backup_type == BackupType.Slip39_Basic:
        prompt = "Create a new wallet\nwith Shamir Backup?"
    elif msg.backup_type == BackupType.Slip39_Advanced:
        prompt = "Create a new wallet\nwith Super Shamir?"
    else:
        prompt = "Do you want to create\na new wallet?"
    await require(confirm_reset_device(ctx, prompt))
    await LoadingAnimation()

    # wipe storage to make sure the device is in a clear state
    storage.reset()

    # request and set new PIN
    if msg.pin_protection:
        newpin = await request_pin_confirm(ctx)
        if not config.change_pin(pin_to_int(""), pin_to_int(newpin), None, None):
            raise wire.ProcessError("Failed to set PIN")

    # generate and display internal entropy
    int_entropy = random.bytes(32)
    if __debug__:
        debug.reset_internal_entropy = int_entropy
    if msg.display_random:
        await layout.show_internal_entropy(ctx, int_entropy)

    # request external entropy and compute the master secret
    entropy_ack = await ctx.call(EntropyRequest(), EntropyAck)
    ext_entropy = entropy_ack.entropy
    # For SLIP-39 this is the Encrypted Master Secret
    secret = _compute_secret_from_entropy(int_entropy, ext_entropy, msg.strength)

    # Check backup type, perform type-specific handling
    if msg.backup_type == BackupType.Bip39:
        # in BIP-39 we store mnemonic string instead of the secret
        secret = bip39.from_data(secret).encode()
    elif msg.backup_type in (BackupType.Slip39_Basic, BackupType.Slip39_Advanced):
        # generate and set SLIP39 parameters
        storage.device.set_slip39_identifier(slip39.generate_random_identifier())
        storage.device.set_slip39_iteration_exponent(slip39.DEFAULT_ITERATION_EXPONENT)
    else:
        # Unknown backup type.
        raise RuntimeError

    # If either of skip_backup or no_backup is specified, we are not doing backup now.
    # Otherwise, we try to do it.
    perform_backup = not msg.no_backup and not msg.skip_backup

    # If doing backup, ask the user to confirm.
    if perform_backup:
        perform_backup = await confirm_backup(ctx)

    # generate and display backup information for the master secret
    if perform_backup:
        await backup_seed(ctx, msg.backup_type, secret)

    # write settings and master secret into storage
    if msg.label is not None:
        storage.device.set_label(msg.label)
    storage.device.set_passphrase_enabled(bool(msg.passphrase_protection))
    storage.device.store_mnemonic_secret(
        secret,  # for SLIP-39, this is the EMS
        msg.backup_type,
        needs_backup=not perform_backup,
        no_backup=msg.no_backup,
    )

    # if we backed up the wallet, show success message
    if perform_backup:
        await layout.show_backup_success(ctx)

    return Success(message="Initialized")


async def backup_slip39_basic(
    ctx: wire.Context, encrypted_master_secret: bytes
) -> None:
    # get number of shares
    await layout.slip39_show_checklist(ctx, 0, BackupType.Slip39_Basic)
    shares_count = await layout.slip39_prompt_number_of_shares(ctx)

    # get threshold
    await layout.slip39_show_checklist(ctx, 1, BackupType.Slip39_Basic)
    threshold = await layout.slip39_prompt_threshold(ctx, shares_count)

    # generate the mnemonics
    mnemonics = slip39.split_ems(
        1,  # Single Group threshold
        [(threshold, shares_count)],  # Single Group threshold/count
        storage.device.get_slip39_identifier(),
        storage.device.get_slip39_iteration_exponent(),
        encrypted_master_secret,
    )[0]

    # show and confirm individual shares
    await layout.slip39_show_checklist(ctx, 2, BackupType.Slip39_Basic)
    await layout.slip39_basic_show_and_confirm_shares(ctx, mnemonics)


async def backup_slip39_advanced(
    ctx: wire.Context, encrypted_master_secret: bytes
) -> None:
    # get number of groups
    await layout.slip39_show_checklist(ctx, 0, BackupType.Slip39_Advanced)
    groups_count = await layout.slip39_advanced_prompt_number_of_groups(ctx)

    # get group threshold
    await layout.slip39_show_checklist(ctx, 1, BackupType.Slip39_Advanced)
    group_threshold = await layout.slip39_advanced_prompt_group_threshold(
        ctx, groups_count
    )

    # get shares and thresholds
    await layout.slip39_show_checklist(ctx, 2, BackupType.Slip39_Advanced)
    groups = []
    for i in range(groups_count):
        share_count = await layout.slip39_prompt_number_of_shares(ctx, i)
        share_threshold = await layout.slip39_prompt_threshold(ctx, share_count, i)
        groups.append((share_threshold, share_count))

    # generate the mnemonics
    mnemonics = slip39.split_ems(
        group_threshold=group_threshold,
        groups=groups,
        identifier=storage.device.get_slip39_identifier(),
        iteration_exponent=storage.device.get_slip39_iteration_exponent(),
        encrypted_master_secret=encrypted_master_secret,
    )

    # show and confirm individual shares
    await layout.slip39_advanced_show_and_confirm_shares(ctx, mnemonics)


def _validate_reset_device(msg: ResetDevice) -> None:
    msg.backup_type = msg.backup_type or _DEFAULT_BACKUP_TYPE
    if msg.backup_type not in (
        BackupType.Bip39,
        BackupType.Slip39_Basic,
        BackupType.Slip39_Advanced,
    ):
        raise wire.ProcessError("Backup type not implemented.")
    if backup_types.is_slip39_backup_type(msg.backup_type):
        if msg.strength not in (128, 256):
            raise wire.ProcessError("Invalid strength (has to be 128 or 256 bits)")
    else:  # BIP-39
        if msg.strength not in (128, 192, 256):
            raise wire.ProcessError("Invalid strength (has to be 128, 192 or 256 bits)")
    if msg.display_random and (msg.skip_backup or msg.no_backup):
        raise wire.ProcessError("Can't show internal entropy when backup is skipped")
    if storage.device.is_initialized():
        raise wire.UnexpectedMessage("Already initialized")


def _compute_secret_from_entropy(
    int_entropy: bytes, ext_entropy: bytes, strength_in_bytes: int
) -> bytes:
    # combine internal and external entropy
    ehash = hashlib.sha256()
    ehash.update(int_entropy)
    ehash.update(ext_entropy)
    entropy = ehash.digest()
    # take a required number of bytes
    strength = strength_in_bytes // 8
    secret = entropy[:strength]
    return secret


async def backup_seed(
    ctx: wire.Context, backup_type: BackupType, mnemonic_secret: bytes
):
    if backup_type == BackupType.Slip39_Basic:
        await backup_slip39_basic(ctx, mnemonic_secret)
    elif backup_type == BackupType.Slip39_Advanced:
        await backup_slip39_advanced(ctx, mnemonic_secret)
    else:
        await layout.bip39_show_and_confirm_mnemonic(ctx, mnemonic_secret.decode())
