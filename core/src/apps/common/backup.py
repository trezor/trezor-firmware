from typing import TYPE_CHECKING

import storage.cache as storage_cache
from trezor import wire
from trezor.enums import MessageType

if TYPE_CHECKING:
    from trezor.wire import Handler, Msg


def repeated_backup_enabled() -> bool:
    return storage_cache.get_bool(storage_cache.APP_RECOVERY_REPEATED_BACKUP_UNLOCKED)


def activate_repeated_backup() -> None:
    storage_cache.set_bool(storage_cache.APP_RECOVERY_REPEATED_BACKUP_UNLOCKED, True)
    wire.filters.append(_repeated_backup_filter)


def deactivate_repeated_backup() -> None:
    storage_cache.delete(storage_cache.APP_RECOVERY_REPEATED_BACKUP_UNLOCKED)
    wire.remove_filter(_repeated_backup_filter)


_ALLOW_WHILE_REPEATED_BACKUP_UNLOCKED = (
    MessageType.Initialize,
    MessageType.GetFeatures,
    MessageType.EndSession,
    MessageType.BackupDevice,
    MessageType.WipeDevice,
    MessageType.Cancel,
)


def _repeated_backup_filter(msg_type: int, prev_handler: Handler[Msg]) -> Handler[Msg]:
    if msg_type in _ALLOW_WHILE_REPEATED_BACKUP_UNLOCKED:
        return prev_handler
    else:
        raise wire.ProcessError("Operation not allowed when in repeated backup state")
