from trezor import loop, utils, wire
from trezor.crypto.hashlib import sha256
from trezor.errors import (
    GroupThresholdReachedError,
    IdentifierMismatchError,
    MnemonicError,
    ShareAlreadyAddedError,
)
from trezor.messages import BackupType
from trezor.messages.Success import Success

from . import recover

from apps.common import mnemonic, storage
from apps.common.layout import show_success
from apps.management.recovery_device import backup_types, layout

if False:
    from typing import List


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

    if not in_progress:  # invalid and inconsistent state
        raise RuntimeError
    if not word_count:  # the first run, prompt word count from the user
        word_count = await _request_and_store_word_count(ctx, dry_run)

    possible_backup_types = backup_types.get(word_count)

    secret = await _request_secret(ctx, word_count, possible_backup_types, dry_run)

    if dry_run:
        result = await _finish_recovery_dry_run(ctx, secret, possible_backup_types)
    else:
        result = await _finish_recovery(ctx, secret, possible_backup_types)
    return result


async def _finish_recovery_dry_run(
    ctx: wire.Context, secret: bytes, possible_backup_types: list
) -> Success:
    digest_input = sha256(secret).digest()
    stored = mnemonic.get_secret()
    digest_stored = sha256(stored).digest()
    result = utils.consteq(digest_stored, digest_input)

    is_slip39 = backup_types.is_slip39(possible_backup_types)

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


async def _finish_recovery(
    ctx: wire.Context, secret: bytes, possible_backup_types: list
) -> Success:
    if len(possible_backup_types) != 1:
        # Only one possible backup type should be left before storing into the storage.
        raise RuntimeError
    storage.device.store_mnemonic_secret(
        secret, possible_backup_types[0], needs_backup=False, no_backup=False
    )
    if backup_types.is_slip39(possible_backup_types):
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


async def _request_secret(
    ctx: wire.Context, word_count: int, possible_backup_types: list, dry_run: bool
) -> bytes:
    is_slip39 = backup_types.is_slip39(possible_backup_types)
    await _request_share_first_screen(ctx, word_count, is_slip39)

    mnemonics = None
    secret = None
    while secret is None:
        group_count = storage.recovery.get_slip39_group_count()
        if group_count:
            mnemonics = storage.recovery_shares.fetch()
            if group_count == 1:
                if BackupType.Slip39_Advanced in possible_backup_types:
                    possible_backup_types.remove(BackupType.Slip39_Advanced)
            else:  # group_count > 1
                if BackupType.Slip39_Basic in possible_backup_types:
                    possible_backup_types.remove(BackupType.Slip39_Basic)
                group_threshold = storage.recovery.get_slip39_group_threshold()
                shares_remaining = storage.recovery.fetch_slip39_remaining_shares()
                await _show_remaining_groups_and_shares(
                    ctx, group_threshold, shares_remaining
                )

        try:
            # ask for mnemonic words one by one
            words = await layout.request_mnemonic(
                ctx, word_count, mnemonics, possible_backup_types
            )
        except IdentifierMismatchError:
            await layout.show_identifier_mismatch(ctx)
            continue
        except ShareAlreadyAddedError:
            await layout.show_share_already_added(ctx)
            continue
        # process this seed share
        try:
            if not is_slip39:
                secret = recover.process_bip39(words)
            else:
                try:
                    secret, group_index, share_index = recover.process_slip39(words)
                except GroupThresholdReachedError:
                    await layout.show_group_threshold_reached(ctx)
                    continue
        except MnemonicError:
            await layout.show_invalid_mnemonic(ctx, is_slip39)
            if group_count is None:  # first mnemonic
                word_count = await _request_and_store_word_count(ctx, dry_run)
                possible_backup_types = backup_types.get(word_count)
            continue
        if secret is None:
            group_count = storage.recovery.get_slip39_group_count()
            if group_count and group_count > 1:
                await layout.show_group_share_success(ctx, share_index, group_index)
            await _request_share_next_screen(ctx, is_slip39)

    # if we have a secret and two possible backup_types
    # it means the slip39 share was 1of1 and the group was 1ofX
    if len(possible_backup_types) != 1:
        group_count = storage.recovery.get_slip39_group_count()
        if group_count == 1:
            possible_backup_types.remove(BackupType.Slip39_Advanced)
        else:
            possible_backup_types.remove(BackupType.Slip39_Basic)

    return secret


async def _request_share_first_screen(
    ctx: wire.Context, word_count: int, is_slip39: bool
) -> None:
    if is_slip39:
        remaining = storage.recovery.fetch_slip39_remaining_shares()
        if remaining:
            await _request_share_next_screen(ctx, is_slip39)
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


async def _request_share_next_screen(ctx: wire.Context, is_slip39: bool) -> None:
    if is_slip39:
        remaining = storage.recovery.fetch_slip39_remaining_shares()
        group_count = storage.recovery.get_slip39_group_count()
        if not remaining:
            # 'remaining' should be stored at this point
            raise RuntimeError

        if group_count > 1:
            content = layout.RecoveryHomescreen(
                "More shares needed", "for this recovery"
            )
            await layout.homescreen_dialog(ctx, content, "Enter share")
        else:
            if remaining[0] == 1:
                text = "1 more share"
            else:
                text = "%d more shares" % remaining[0]
            content = layout.RecoveryHomescreen(text, "needed to enter")
            await layout.homescreen_dialog(ctx, content, "Enter share")
    else:
        raise RuntimeError


async def _show_remaining_groups_and_shares(
    ctx: wire.Context, group_threshold: int, shares_remaining: List[int]
) -> None:
    identifiers = []

    first_entered_index = -1
    for i in range(len(shares_remaining)):
        if shares_remaining[i] < 16:
            first_entered_index = i

    for i, r in enumerate(shares_remaining):
        if 0 < r < 16:
            identifier = storage.recovery_shares.fetch_group(i)[0].split(" ")[0:3]
            identifiers.append([r, identifier])
        elif r == 16:
            identifier = storage.recovery_shares.fetch_group(first_entered_index)[
                0
            ].split(" ")[0:2]
            try:
                # we only add the group (two words) identifier once
                identifiers.index([r, identifier])
            except ValueError:
                identifiers.append([r, identifier])

    return await layout.show_remaining_shares(
        ctx, identifiers, group_threshold, shares_remaining
    )
