from trezor import loop, utils, wire
from trezor.crypto.hashlib import sha256
from trezor.crypto.slip39 import MAX_SHARE_COUNT, Share
from trezor.errors import MnemonicError
from trezor.messages import BackupType
from trezor.messages.Success import Success

from . import recover

from apps.common import mnemonic, storage
from apps.common.layout import show_success
from apps.management import backup_types
from apps.management.recovery_device import layout

if False:
    from typing import Optional, Tuple
    from trezor.messages.ResetDevice import EnumTypeBackupType


async def recovery_homescreen() -> None:
    # recovery process does not communicate on the wire
    ctx = wire.DummyContext()
    try:
        await recovery_process(ctx)
    finally:
        # clear the loop state, so loop.run will exit
        loop.clear()
        # clear the registered wire handlers to avoid conflicts
        wire.clear()


async def recovery_process(ctx: wire.Context) -> Success:
    try:
        result = await _continue_recovery_process(ctx)
    except recover.RecoveryAborted:
        dry_run = storage.recovery.is_dry_run()
        if dry_run:
            storage.recovery.end_progress()
        else:
            storage.wipe()
        raise wire.ActionCancelled("Cancelled")
    return result


async def _continue_recovery_process(ctx: wire.Context) -> Success:
    # gather the current recovery state from storage
    in_progress = storage.recovery.is_in_progress()
    word_count = storage.recovery.get_word_count()
    dry_run = storage.recovery.is_dry_run()
    backup_type = storage.recovery.get_backup_type()

    if not in_progress:  # invalid and inconsistent state
        raise RuntimeError
    if not word_count:  # the first run, prompt word count from the user
        word_count = await _request_and_store_word_count(ctx, dry_run)

    secret = await _request_secret(ctx, word_count, dry_run, backup_type)

    if dry_run:
        result = await _finish_recovery_dry_run(ctx, secret)
    else:
        result = await _finish_recovery(ctx, secret)

    return result


async def _request_secret(
    ctx: wire.Context,
    word_count: int,
    dry_run: bool,
    backup_type: Optional[EnumTypeBackupType],
) -> bytes:
    is_slip39 = backup_types.is_slip39_word_count(word_count)
    await _request_share_first_screen(ctx, word_count, is_slip39)

    secret = None
    while secret is None:
        # ask for mnemonic words one by one
        words = await layout.request_mnemonic(ctx, word_count, backup_type)

        # if they were invalid or some checks failed we continue and request them again
        if not words:
            continue

        try:
            secret, backup_type = await _process_words(
                ctx, words, is_slip39, backup_type
            )
        except MnemonicError:
            await layout.show_invalid_mnemonic(ctx, is_slip39)
            # If the backup type is not stored, we have processed zero mnemonics.
            # In that case we prompt the word count again to give the user an
            # opportunity to change the word count if they've made a mistake.
            first_mnemonic = storage.recovery.get_backup_type() is None
            if first_mnemonic:
                word_count = await _request_and_store_word_count(ctx, dry_run)
                is_slip39 = backup_types.is_slip39_word_count(word_count)
                backup_type = None
            continue

    return secret


async def _finish_recovery_dry_run(ctx: wire.Context, secret: bytes) -> Success:
    backup_type = storage.recovery.get_backup_type()
    if backup_type is None:
        raise RuntimeError

    digest_input = sha256(secret).digest()
    stored = mnemonic.get_secret()
    digest_stored = sha256(stored).digest()
    result = utils.consteq(digest_stored, digest_input)

    is_slip39 = backup_types.is_slip39_backup_type(backup_type)
    # Check that the identifier and iteration exponent match as well
    if is_slip39:
        result &= (
            storage.device.get_slip39_identifier()
            == storage.recovery.get_slip39_identifier()
        )
        result &= (
            storage.device.get_slip39_iteration_exponent()
            == storage.recovery.get_slip39_iteration_exponent()
        )

    await layout.show_dry_run_result(ctx, result, is_slip39)

    storage.recovery.end_progress()

    if result:
        return Success("The seed is valid and matches the one in the device")
    else:
        raise wire.ProcessError("The seed does not match the one in the device")


async def _finish_recovery(ctx: wire.Context, secret: bytes) -> Success:
    backup_type = storage.recovery.get_backup_type()
    if backup_type is None:
        raise RuntimeError

    storage.device.store_mnemonic_secret(
        secret, backup_type, needs_backup=False, no_backup=False
    )
    if backup_type in (BackupType.Slip39_Basic, BackupType.Slip39_Advanced):
        identifier = storage.recovery.get_slip39_identifier()
        exponent = storage.recovery.get_slip39_iteration_exponent()
        if identifier is None or exponent is None:
            # Identifier and exponent need to be stored in storage at this point
            raise RuntimeError
        storage.device.set_slip39_identifier(identifier)
        storage.device.set_slip39_iteration_exponent(exponent)

    await show_success(ctx, ("You have successfully", "recovered your wallet."))

    storage.recovery.end_progress()
    return Success(message="Device recovered")


async def _request_and_store_word_count(ctx: wire.Context, dry_run: bool) -> int:
    homepage = layout.RecoveryHomescreen("Select number of words")
    await layout.homescreen_dialog(ctx, homepage, "Select")

    # ask for the number of words
    word_count = await layout.request_word_count(ctx, dry_run)

    # save them into storage
    storage.recovery.set_word_count(word_count)

    return word_count


async def _process_words(
    ctx: wire.Context,
    words: str,
    is_slip39: bool,
    backup_type: Optional[EnumTypeBackupType],
) -> Tuple[Optional[bytes], EnumTypeBackupType]:

    share = None
    if not is_slip39:  # BIP-39
        secret = recover.process_bip39(words)
    else:
        secret, share = recover.process_slip39(words)

    if backup_type is None:
        # we have to decide what backup type this is and store it
        backup_type = _store_backup_type(is_slip39, share)

    if secret is None:
        if share.group_count and share.group_count > 1:
            await layout.show_group_share_success(ctx, share.index, share.group_index)
        await _request_share_next_screen(ctx)

    return secret, backup_type


def _store_backup_type(is_slip39: bool, share: Share = None) -> EnumTypeBackupType:
    if not is_slip39:  # BIP-39
        backup_type = BackupType.Bip39
    elif not share or share.group_count < 1:  # invalid parameters
        raise RuntimeError
    elif share.group_count == 1:
        backup_type = BackupType.Slip39_Basic
    else:
        backup_type = BackupType.Slip39_Advanced

    storage.recovery.set_backup_type(backup_type)
    return backup_type


async def _request_share_first_screen(
    ctx: wire.Context, word_count: int, is_slip39: bool
) -> None:
    if is_slip39:
        remaining = storage.recovery.fetch_slip39_remaining_shares()
        if remaining:
            await _request_share_next_screen(ctx)
        else:
            content = layout.RecoveryHomescreen(
                "Enter any share", "(%d words)" % word_count
            )
            await layout.homescreen_dialog(ctx, content, "Enter share")
    else:  # BIP-39
        content = layout.RecoveryHomescreen(
            "Enter recovery seed", "(%d words)" % word_count
        )
        await layout.homescreen_dialog(ctx, content, "Enter seed")


async def _request_share_next_screen(ctx: wire.Context) -> None:
    remaining = storage.recovery.fetch_slip39_remaining_shares()
    group_count = storage.recovery.get_slip39_group_count()
    if not remaining:
        # 'remaining' should be stored at this point
        raise RuntimeError

    if group_count > 1:
        content = layout.RecoveryHomescreen("More shares needed")
        await layout.homescreen_dialog(
            ctx, content, "Enter", _show_remaining_groups_and_shares
        )
    else:
        if remaining[0] == 1:
            text = "1 more share"
        else:
            text = "%d more shares" % remaining[0]
        content = layout.RecoveryHomescreen(text, "needed to enter")
        await layout.homescreen_dialog(ctx, content, "Enter share")


async def _show_remaining_groups_and_shares(ctx: wire.Context) -> None:
    """
    Show info dialog for Slip39 Advanced - what shares are to be entered.
    """
    shares_remaining = storage.recovery.fetch_slip39_remaining_shares()

    identifiers = []
    first_entered_index = -1
    for i in range(len(shares_remaining)):
        if shares_remaining[i] < MAX_SHARE_COUNT:
            first_entered_index = i

    for i, r in enumerate(shares_remaining):
        if 0 < r < MAX_SHARE_COUNT:
            identifier = storage.recovery_shares.fetch_group(i)[0].split(" ")[0:3]
            identifiers.append([r, identifier])
        elif r == MAX_SHARE_COUNT:
            identifier = storage.recovery_shares.fetch_group(first_entered_index)[
                0
            ].split(" ")[0:2]
            try:
                # we only add the group (two words) identifier once
                identifiers.index([r, identifier])
            except ValueError:
                identifiers.append([r, identifier])

    return await layout.show_remaining_shares(ctx, identifiers, shares_remaining)
