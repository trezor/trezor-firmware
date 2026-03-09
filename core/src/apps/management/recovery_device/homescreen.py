from typing import TYPE_CHECKING

import storage.device as storage_device
import storage.recovery as storage_recovery
from trezor import TR, utils, wire
from trezor.messages import Success
from trezor.wire import message_handler

from apps.common import backup_types
from apps.common.lock_manager import with_prolonged_suspend_time

from . import layout, recover

if TYPE_CHECKING:
    from trezor.enums import BackupMethod, BackupType, RecoveryType


async def recovery_homescreen() -> None:
    from trezor import workflow

    from apps.common import backup
    from apps.homescreen import homescreen

    if backup.repeated_backup_enabled():
        await _continue_repeated_backup()
    elif not storage_recovery.is_in_progress():
        workflow.set_default(homescreen)
    else:
        # backup method will be chosen by the user
        await recovery_process(None)


@with_prolonged_suspend_time
async def recovery_process(method: BackupMethod | None) -> Success:
    import storage
    from trezor.enums import MessageType, RecoveryType

    from apps.common import backup

    recovery_type = storage_recovery.get_type()

    if utils.USE_THP:
        message_handler.AVOID_RESTARTING_FOR = (
            MessageType.GetFeatures,
            MessageType.EndSession,
        )
    else:
        message_handler.AVOID_RESTARTING_FOR = (
            MessageType.Initialize,
            MessageType.GetFeatures,
            MessageType.EndSession,
        )
    try:
        return await _continue_recovery_process(method)
    except recover.RecoveryAborted:
        storage_recovery.end_progress()
        backup.deactivate_repeated_backup()
        if recovery_type == RecoveryType.NormalRecovery:
            from trezor.wire.context import try_get_ctx_ids

            storage.wipe(clear_cache=False)
            storage.wipe_cache(excluded=try_get_ctx_ids())
        raise wire.ActionCancelled


async def _continue_repeated_backup() -> None:
    from trezor.enums import MessageType

    from apps.common import backup
    from apps.management.backup_device import perform_backup

    if utils.USE_THP:
        message_handler.AVOID_RESTARTING_FOR = (
            MessageType.GetFeatures,
            MessageType.EndSession,
        )
    else:
        message_handler.AVOID_RESTARTING_FOR = (
            MessageType.Initialize,
            MessageType.GetFeatures,
            MessageType.EndSession,
        )

    try:
        # During on-device flow, the backup method will be chosen later.
        await perform_backup(is_repeated_backup=True, method=None)
    finally:
        backup.deactivate_repeated_backup()


async def _recover_secret(
    recovery_type: RecoveryType, method: BackupMethod | None
) -> tuple[bytes, BackupType]:
    handler_type = await layout.choose_handler(method)

    # Show recovery state in the beginning, on some failures, and after a successful share entry.
    is_retry = False

    while True:
        # Load existing recovery state (persisted by _process_words below).
        handler = await handler_type.load(recovery_type)
        await handler.show_state(is_retry)
        is_retry = False

        # Ask for mnemonic words one by one.
        # Returns `None` on cancellation/validation error.
        if (words := await handler.request_mnemonic()) is None:
            continue
        try:
            if (result := await _process_words(words)) is not None:
                return result
            # If _process_words succeeded, at least one share was entered.
        except _RetryEntry:
            is_retry = True  # Retry share entry (without showing recovery state)


async def _continue_recovery_process(method: BackupMethod | None) -> Success:
    from trezor.enums import RecoveryType

    # gather the current recovery state from storage
    recovery_type = storage_recovery.get_type()

    # run recovery process - may raise RecoveryAborted
    secret, backup_type = await _recover_secret(recovery_type, method)

    # finish recovery
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

    storage_device.set_backup_type(backup_type)
    storage_device.store_mnemonic_secret(
        secret=secret,
        needs_backup=False,
        no_backup=False,
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


class _RetryEntry(Exception):
    """Raised after entering an invalid mnemonic."""

    pass


async def _process_words(words: str) -> tuple[bytes, BackupType] | None:
    from trezor.errors import MnemonicError

    word_count = len(words.split(" "))
    is_slip39 = backup_types.is_slip39_word_count(word_count)

    share = None
    try:
        if not is_slip39:  # BIP-39
            secret: bytes | None = recover.process_bip39(words)
        else:
            secret, share = recover.process_slip39(words)
    except MnemonicError:
        from trezor.ui.layouts.recovery import show_invalid_mnemonic

        await show_invalid_mnemonic(word_count)
        raise _RetryEntry

    backup_type = backup_types.infer_backup_type(is_slip39, share)
    if secret is None:  # SLIP-39
        assert share is not None
        if share.group_count and share.group_count > 1:
            await layout.show_group_share_success(share.index, share.group_index)
        return None  # more shares are needed

    return secret, backup_type
