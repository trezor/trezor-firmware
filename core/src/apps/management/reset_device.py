from trezor import config, ui, wire
from trezor.crypto import bip39, hashlib, random, slip39
from trezor.messages import BackupType, ButtonRequestType
from trezor.messages.EntropyAck import EntropyAck
from trezor.messages.EntropyRequest import EntropyRequest
from trezor.messages.Success import Success
from trezor.pin import pin_to_int
from trezor.ui.loader import LoadingAnimation
from trezor.ui.text import Text

from apps.common import storage
from apps.common.confirm import require_confirm
from apps.management.change_pin import request_pin_confirm
from apps.management.common import layout

if __debug__:
    from apps import debug

if False:
    from trezor.messages.ResetDevice import ResetDevice

_DEFAULT_BACKUP_TYPE = BackupType.Bip39


async def reset_device(ctx: wire.Context, msg: ResetDevice) -> Success:
    # validate parameters and device state
    _validate_reset_device(msg)

    # make sure user knows he's setting up a new wallet
    await _show_reset_device_warning(ctx, msg.backup_type)

    # request new PIN
    if msg.pin_protection:
        newpin = await request_pin_confirm(ctx)
    else:
        newpin = ""

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

    if msg.backup_type != BackupType.Bip39:
        storage.device.set_slip39_identifier(slip39.generate_random_identifier())
        storage.device.set_slip39_iteration_exponent(slip39.DEFAULT_ITERATION_EXPONENT)

    # should we back up the wallet now?
    if not msg.no_backup and not msg.skip_backup:
        if not await layout.confirm_backup(ctx):
            if not await layout.confirm_backup_again(ctx):
                msg.skip_backup = True

    # generate and display backup information for the master secret
    if not msg.no_backup and not msg.skip_backup:
        if msg.backup_type == BackupType.Slip39_Basic:
            await backup_slip39_wallet(ctx, secret)
        elif msg.backup_type == BackupType.Slip39_Advanced:
            await backup_group_slip39_wallet(ctx, secret)
        else:
            await backup_bip39_wallet(ctx, secret)

    # write PIN into storage
    if not config.change_pin(pin_to_int(""), pin_to_int(newpin)):
        raise wire.ProcessError("Could not change PIN")

    # write settings and master secret into storage
    storage.device.load_settings(
        label=msg.label, use_passphrase=msg.passphrase_protection
    )
    if msg.backup_type == BackupType.Bip39:
        # in BIP-39 we store mnemonic string instead of the secret
        storage.device.store_mnemonic_secret(
            bip39.from_data(secret).encode(),
            BackupType.Bip39,
            needs_backup=msg.skip_backup,
            no_backup=msg.no_backup,
        )
    elif msg.backup_type in (BackupType.Slip39_Basic, BackupType.Slip39_Advanced):
        storage.device.store_mnemonic_secret(
            secret,  # this is the EMS in SLIP-39 terminology
            msg.backup_type,
            needs_backup=msg.skip_backup,
            no_backup=msg.no_backup,
        )
    else:
        # This check might seem superfluous, because we are checking in `_validate_reset_device`
        # already, however, this is critical part, so just to make sure.
        # Unknown backup type
        raise RuntimeError()

    # if we backed up the wallet, show success message
    if not msg.no_backup and not msg.skip_backup:
        await layout.show_backup_success(ctx)

    return Success(message="Initialized")


async def backup_slip39_wallet(
    ctx: wire.Context, encrypted_master_secret: bytes
) -> None:
    # get number of shares
    await layout.slip39_show_checklist_set_shares(ctx)
    shares_count = await layout.slip39_prompt_number_of_shares(ctx)

    # get threshold
    await layout.slip39_show_checklist_set_threshold(ctx, shares_count)
    threshold = await layout.slip39_prompt_threshold(ctx, shares_count)

    # generate the mnemonics
    mnemonics = slip39.generate_mnemonics_from_data(
        encrypted_master_secret,
        storage.device.get_slip39_identifier(),
        1,  # Single Group threshold
        [(threshold, shares_count)],  # Single Group threshold/count
        storage.device.get_slip39_iteration_exponent(),
    )[0]

    # show and confirm individual shares
    await layout.slip39_show_checklist_show_shares(ctx, shares_count, threshold)
    await layout.slip39_show_and_confirm_shares(ctx, mnemonics)


async def backup_group_slip39_wallet(
    ctx: wire.Context, encrypted_master_secret: bytes
) -> None:
    # get number of groups
    await layout.slip39_group_show_checklist_set_groups(ctx)
    groups_count = await layout.slip39_prompt_number_of_groups(ctx)

    # get group threshold
    await layout.slip39_group_show_checklist_set_group_threshold(ctx, groups_count)
    group_threshold = await layout.slip39_prompt_group_threshold(ctx, groups_count)

    # get shares and thresholds
    await layout.slip39_group_show_checklist_set_shares(
        ctx, groups_count, group_threshold
    )
    groups = []
    for i in range(groups_count):
        share_count = await layout.slip39_prompt_number_of_shares(ctx, i)
        share_threshold = await layout.slip39_prompt_threshold(ctx, share_count, i)
        groups.append((share_threshold, share_count))

    # generate the mnemonics
    mnemonics = slip39.generate_mnemonics_from_data(
        encrypted_master_secret=encrypted_master_secret,
        identifier=storage.device.get_slip39_identifier(),
        group_threshold=group_threshold,
        groups=groups,
        iteration_exponent=storage.device.get_slip39_iteration_exponent(),
    )

    # show and confirm individual shares
    await layout.slip39_group_show_and_confirm_shares(ctx, mnemonics)


async def backup_bip39_wallet(ctx: wire.Context, secret: bytes) -> None:
    mnemonic = bip39.from_data(secret)
    await layout.bip39_show_and_confirm_mnemonic(ctx, mnemonic)


def _validate_reset_device(msg: ResetDevice) -> None:
    msg.backup_type = msg.backup_type or _DEFAULT_BACKUP_TYPE
    if msg.backup_type not in (
        BackupType.Bip39,
        BackupType.Slip39_Basic,
        BackupType.Slip39_Advanced,
    ):
        raise wire.ProcessError("Backup type not implemented.")
    if msg.strength not in (128, 256):
        if msg.backup_type == BackupType.Slip39_Basic:
            raise wire.ProcessError("Invalid strength (has to be 128 or 256 bits)")
        elif msg.strength != 192:
            raise wire.ProcessError("Invalid strength (has to be 128, 192 or 256 bits)")
    if msg.display_random and (msg.skip_backup or msg.no_backup):
        raise wire.ProcessError("Can't show internal entropy when backup is skipped")
    if storage.is_initialized():
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


async def _show_reset_device_warning(ctx, backup_type: BackupType = BackupType.Bip39):
    text = Text("Create new wallet", ui.ICON_RESET, new_lines=False)
    if backup_type == BackupType.Slip39_Basic:
        text.bold("Create a new wallet")
        text.br()
        text.bold("with Shamir Backup?")
    elif backup_type == BackupType.Slip39_Advanced:
        text.bold("Create a new wallet")
        text.br()
        text.bold("with Super Shamir?")
    else:
        text.bold("Do you want to create")
        text.br()
        text.bold("a new wallet?")
    text.br()
    text.br_half()
    text.normal("By continuing you agree")
    text.br()
    text.normal("to")
    text.bold("https://trezor.io/tos")
    await require_confirm(ctx, text, ButtonRequestType.ResetDevice, major_confirm=True)
    await LoadingAnimation()
