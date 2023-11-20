from typing import TYPE_CHECKING

import storage.device as storage_device
import storage.recovery as storage_recovery
import storage.recovery_shares as storage_recovery_shares
from trezor import TR, wire
from trezor.messages import Success

from apps.common import backup_types

from . import layout, recover

if TYPE_CHECKING:
    from trezor.enums import BackupType, RecoveryType

    from .layout import RemainingSharesInfo


async def recovery_homescreen() -> None:
    from trezor import workflow

    from apps.common import backup
    from apps.homescreen import homescreen

    if backup.repeated_backup_enabled():
        await _continue_repeated_backup()
    elif not storage_recovery.is_in_progress():
        workflow.set_default(homescreen)
    else:
        await recovery_process()


async def recovery_process() -> Success:
    import storage
    from trezor.enums import MessageType, RecoveryType

    from apps.common import backup

    recovery_type = storage_recovery.get_type()

    wire.AVOID_RESTARTING_FOR = (
        MessageType.Initialize,
        MessageType.GetFeatures,
        MessageType.EndSession,
    )
    try:
        return await _continue_recovery_process()
    except recover.RecoveryAborted:
        storage_recovery.end_progress()
        backup.deactivate_repeated_backup()
        if recovery_type == RecoveryType.NormalRecovery:
            storage.wipe()
        raise wire.ActionCancelled


async def _continue_repeated_backup() -> None:
    from trezor.enums import MessageType

    from apps.common import backup
    from apps.management.backup_device import perform_backup

    wire.AVOID_RESTARTING_FOR = (
        MessageType.Initialize,
        MessageType.GetFeatures,
        MessageType.EndSession,
    )

    try:
        await perform_backup(is_repeated_backup=True)
    finally:
        backup.deactivate_repeated_backup()


async def _continue_recovery_process() -> Success:
    from trezor import utils
    from trezor.enums import RecoveryType
    from trezor.errors import MnemonicError

    # gather the current recovery state from storage
    recovery_type = storage_recovery.get_type()
    word_count, backup_type = recover.load_slip39_state()

    # Both word_count and backup_type are derived from the same data. Both will be
    # either set or unset. We use 'backup_type is None' to detect status of both.
    # The following variable indicates that we are (re)starting the first recovery step,
    # which includes word count selection.
    is_first_step = backup_type is None

    if not is_first_step:
        assert word_count is not None
        # If we continue recovery, show starting screen with word count immediately.
        await _request_share_first_screen(word_count, recovery_type)

    secret = None
    while secret is None:
        if is_first_step:
            # If we are starting recovery, ask for word count first...
            # _request_word_count
            # For others than model_tr, just continue straight to word count keyboard
            # pylint: disable-next=consider-using-in
            if utils.INTERNAL_MODEL == "T2B1" or utils.INTERNAL_MODEL == "T3B1":
                await layout.homescreen_dialog(
                    TR.buttons__continue, TR.recovery__num_of_words
                )
            # ask for the number of words
            word_count = await layout.request_word_count(recovery_type)
            # ...and only then show the starting screen with word count.
            await _request_share_first_screen(word_count, recovery_type)
        assert word_count is not None

        # ask for mnemonic words one by one
        words = await layout.request_mnemonic(word_count, backup_type)

        # if they were invalid or some checks failed we continue and request them again
        if not words:
            continue

        try:
            secret, backup_type = await _process_words(words)
            # If _process_words succeeded, we now have both backup_type (from
            # its result) and word_count (from _request_word_count earlier), which means
            # that the first step is complete.
            is_first_step = False
        except MnemonicError:
            await layout.show_invalid_mnemonic(word_count)

    assert backup_type is not None
    if recovery_type == RecoveryType.DryRun:
        result = await _finish_recovery_dry_run(secret, backup_type)
    elif recovery_type == RecoveryType.UnlockRepeatedBackup:
        result = await _finish_recovery_unlock_repeated_backup(secret, backup_type)
    else:
        result = await _finish_recovery(secret, backup_type)

    return result


def _check_secret_against_stored_secret(
    secret: bytes, is_slip39: bool, backup_type: BackupType
) -> bool:
    from trezor import utils
    from trezor.crypto.hashlib import sha256

    from apps.common import mnemonic

    digest_input = sha256(secret).digest()
    stored = mnemonic.get_secret()
    digest_stored = sha256(stored).digest()
    result = utils.consteq(digest_stored, digest_input)

    is_slip39 = backup_types.is_slip39_backup_type(backup_type)
    # Check that the identifier, extendable backup flag and iteration exponent match as well
    if is_slip39:
        if not backup_types.is_extendable_backup_type(backup_type):
            result &= (
                storage_device.get_slip39_identifier()
                == storage_recovery.get_slip39_identifier()
            )
        result &= backup_types.is_extendable_backup_type(
            storage_device.get_backup_type()
        ) == backup_types.is_extendable_backup_type(backup_type)
        result &= (
            storage_device.get_slip39_iteration_exponent()
            == storage_recovery.get_slip39_iteration_exponent()
        )

    return result


async def _finish_recovery_dry_run(secret: bytes, backup_type: BackupType) -> Success:
    if backup_type is None:
        raise RuntimeError

    is_slip39 = backup_types.is_slip39_backup_type(backup_type)

    result = _check_secret_against_stored_secret(secret, is_slip39, backup_type)

    storage_recovery.end_progress()

    await layout.show_dry_run_result(result, is_slip39)

    if result:
        return Success(message="The seed is valid and matches the one in the device")
    else:
        raise wire.ProcessError("The seed does not match the one in the device")


async def _finish_recovery_unlock_repeated_backup(
    secret: bytes, backup_type: BackupType
) -> Success:
    from apps.common import backup

    if backup_type is None:
        raise RuntimeError

    is_slip39 = backup_types.is_slip39_backup_type(backup_type)

    result = _check_secret_against_stored_secret(secret, is_slip39, backup_type)

    storage_recovery.end_progress()

    if result:
        backup.activate_repeated_backup()
        return Success(message="Backup unlocked")
    else:
        raise wire.ProcessError("The seed does not match the one in the device")


async def _finish_recovery(secret: bytes, backup_type: BackupType) -> Success:
    from trezor.ui.layouts import show_success

    if backup_type is None:
        raise RuntimeError

    storage_device.store_mnemonic_secret(
        secret, backup_type, needs_backup=False, no_backup=False
    )
    if backup_types.is_slip39_backup_type(backup_type):
        if not backup_types.is_extendable_backup_type(backup_type):
            identifier = storage_recovery.get_slip39_identifier()
            if identifier is None:
                # The identifier needs to be stored in storage at this point
                raise RuntimeError
            storage_device.set_slip39_identifier(identifier)

        exponent = storage_recovery.get_slip39_iteration_exponent()
        if exponent is None:
            # The iteration exponent needs to be stored in storage at this point
            raise RuntimeError
        storage_device.set_slip39_iteration_exponent(exponent)

    storage_recovery.end_progress()

    await show_success("success_recovery", TR.recovery__wallet_recovered)
    return Success(message="Device recovered")


async def _process_words(words: str) -> tuple[bytes | None, BackupType]:
    word_count = len(words.split(" "))
    is_slip39 = backup_types.is_slip39_word_count(word_count)

    share = None
    if not is_slip39:  # BIP-39
        secret: bytes | None = recover.process_bip39(words)
    else:
        secret, share = recover.process_slip39(words)

    backup_type = backup_types.infer_backup_type(is_slip39, share)
    if secret is None:  # SLIP-39
        assert share is not None
        if share.group_count and share.group_count > 1:
            await layout.show_group_share_success(share.index, share.group_index)
        await _request_share_next_screen()

    return secret, backup_type


async def _request_share_first_screen(
    word_count: int, recovery_type: RecoveryType
) -> None:
    from trezor.enums import RecoveryType

    if backup_types.is_slip39_word_count(word_count):
        remaining = storage_recovery.fetch_slip39_remaining_shares()
        if remaining:
            await _request_share_next_screen()
        else:
            if recovery_type == RecoveryType.UnlockRepeatedBackup:
                text = TR.recovery__enter_backup
                button_label = TR.buttons__continue
            else:
                text = TR.recovery__enter_any_share
                button_label = TR.buttons__enter_share
            await layout.homescreen_dialog(
                button_label,
                text,
                TR.recovery__word_count_template.format(word_count),
                show_instructions=True,
            )
    else:  # BIP-39
        await layout.homescreen_dialog(
            TR.buttons__continue,
            TR.recovery__enter_backup,
            TR.recovery__word_count_template.format(word_count),
            show_instructions=True,
        )


async def _request_share_next_screen() -> None:
    remaining = storage_recovery.fetch_slip39_remaining_shares()
    group_count = storage_recovery.get_slip39_group_count()
    if not remaining:
        # 'remaining' should be stored at this point
        raise RuntimeError

    if group_count > 1:
        await layout.enter_share(
            remaining_shares_info=_get_remaining_groups_and_shares()
        )
    else:
        entered = len(storage_recovery_shares.fetch_group(0))
        await layout.enter_share(entered_remaining=(entered, remaining[0]))


def _get_remaining_groups_and_shares() -> "RemainingSharesInfo":
    """
    Prepare data for Slip39 Advanced - what shares are to be entered.
    """
    from trezor.crypto import slip39

    shares_remaining = storage_recovery.fetch_slip39_remaining_shares()
    assert shares_remaining  # should be stored at this point

    groups = set()
    first_entered_index = -1
    for i, group_count in enumerate(shares_remaining):
        if group_count < slip39.MAX_SHARE_COUNT:
            first_entered_index = i
            break

    share = None
    for index, remaining in enumerate(shares_remaining):
        if 0 <= remaining < slip39.MAX_SHARE_COUNT:
            m = storage_recovery_shares.fetch_group(index)[0]
            if not share:
                share = slip39.decode_mnemonic(m)
            identifier = tuple(m.split(" ")[0:3])
            groups.add(identifier)
        elif remaining == slip39.MAX_SHARE_COUNT:  # no shares yet
            identifier = tuple(
                storage_recovery_shares.fetch_group(first_entered_index)[0].split(" ")[
                    0:2
                ]
            )
            groups.add(identifier)

    assert share  # share needs to be set
    return groups, shares_remaining, share.group_threshold
