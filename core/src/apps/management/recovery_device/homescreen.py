from typing import TYPE_CHECKING, Awaitable, Protocol

import storage.device as storage_device
import storage.recovery as storage_recovery
import storage.recovery_shares as storage_recovery_shares
from trezor import TR, utils, wire
from trezor.messages import Success
from trezor.wire import message_handler

from apps.common import backup_types
from apps.management.recovery_device.recover import RecoveryAborted

from . import layout, recover

if TYPE_CHECKING:
    from trezor.enums import BackupMethod, BackupType, RecoveryType

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
        # backup method will be chosen by the user
        await recovery_process(None)


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


if TYPE_CHECKING:

    class RecoveryHandler(Protocol):
        @classmethod
        async def load(cls, recovery_type: RecoveryType) -> "RecoveryHandler": ...

        async def show_state(self, is_retry: bool) -> None: ...
        async def request_mnemonic(self) -> str | None: ...


class _DisplayHandler:
    def __init__(
        self,
        recovery_type: RecoveryType,
        word_count: int,
        backup_type: BackupType | None,
    ) -> None:
        self.recovery_type = recovery_type
        self.word_count = word_count
        self.backup_type = backup_type

    @classmethod
    async def load(cls, recovery_type: RecoveryType) -> "RecoveryHandler":
        # `slip39_state is None` indicates that we are (re)starting the first recovery step,
        # which includes word count selection.
        if (slip39_state := recover.load_slip39_state()) is None:
            # If we are starting recovery, ask for word count first...
            try:
                word_count = await layout.request_word_count(recovery_type)
            except wire.ActionCancelled:
                raise RecoveryAborted
            # ...and only then show the starting screen with word count.
            # Backup type will be deduced from the first share.
            backup_type = None
        else:
            # SLIP-39 recovery is ongoing (at least one share was entered).
            word_count, backup_type = slip39_state

        return cls(recovery_type, word_count, backup_type)

    async def show_state(self, is_retry: bool) -> None:
        if is_retry and self.backup_type is not None:
            # don't show recovery state on retries (if first share was entered)
            return
        await _request_share_first_screen(self.word_count, self.recovery_type)

    async def request_mnemonic(self) -> str | None:
        """Return the mnemonic or `None` on cancellation/validation error."""
        from .word_validity import WordValidityResult

        try:
            # returns `None` on cancellation
            return await layout.request_mnemonic(self.word_count, self.backup_type)
        except WordValidityResult as exc:
            # if they were invalid or some checks failed we continue and request them again
            await exc.show_error()
            return None


if not utils.USE_N4W1:

    async def _choose_handler(method: BackupMethod | None) -> type[RecoveryHandler]:
        from trezor.enums import BackupMethod

        if method is not BackupMethod.Display and __debug__:
            from trezor import log

            log.warning(__name__, "Unsupported backup method: %s", method)

        return _DisplayHandler

else:

    async def _choose_handler(method: BackupMethod | None) -> type[RecoveryHandler]:
        if method is None:
            from .layout import _choose_method

            method = await _choose_method()

        return (_DisplayHandler, _N4W1Handler)[method]

    class _N4W1Handler:
        def __init__(
            self,
            recovery_type: RecoveryType,
            slip39_state: recover.Slip39State | None,
        ) -> None:
            super().__init__()
            self.recovery_type = recovery_type
            # `slip39_state is None` indicates that we are (re)starting the first recovery step.
            self.backup_type = slip39_state and slip39_state[1]
            self.word_count = 20  # TODO: improve

        @classmethod
        async def load(cls, recovery_type: RecoveryType) -> "RecoveryHandler":
            return cls(recovery_type, recover.load_slip39_state())

        async def show_state(self, is_retry: bool) -> None:
            if is_retry or self.backup_type is None:
                # don't show recovery state on retries and before the first share is entered
                return
            await _request_share_first_screen(self.word_count, self.recovery_type)

        async def request_mnemonic(self) -> str | None:
            """Return the mnemonic or `None` on cancellation/validation error."""
            from apps.debug import n4w1_mock

            from .word_validity import WordValidityResult, check

            with n4w1_mock.ctx as ctx:
                # returns `None` on cancellation or retriable error.
                blob = await layout._n4w1_read(
                    ctx, description=TR.n4w1__hold_next, button=TR.n4w1__footer_next
                )

            if blob is None:
                return None

            # TODO: use protobuf?
            share = blob.decode()
            share_words = share.split(" ")
            try:
                # Re-verify relevant prefixes
                # TODO: can it be encapsulated too?
                for prefix_len in range(1, 5):
                    check(self.backup_type, share_words[:prefix_len])
                return share
            except WordValidityResult as exc:
                # if they were invalid or some checks failed we continue and request them again
                await exc.show_error()
                return None

        def show_invalid_mnemonic(self) -> Awaitable[None]:
            from trezor.ui.layouts.recovery import show_invalid_mnemonic

            return show_invalid_mnemonic(self.word_count)


async def _recover_secret(
    recovery_type: RecoveryType, method: BackupMethod | None
) -> tuple[bytes, BackupType]:
    from trezor.errors import MnemonicError

    handler_type = await _choose_handler(method)

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


async def _request_share_first_screen(
    word_count: int, recovery_type: RecoveryType
) -> None:
    from trezor.enums import RecoveryType

    if backup_types.is_slip39_word_count(word_count):
        remaining = storage_recovery.fetch_slip39_remaining_shares()
        if remaining:
            group_count = storage_recovery.get_slip39_group_count()
            if group_count > 1:
                await layout.enter_share(
                    remaining_shares_info=_get_remaining_groups_and_shares()
                )
            else:
                entered = len(storage_recovery_shares.fetch_group(0))
                await layout.enter_share(entered_remaining=(entered, remaining[0]))
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
