from typing import TYPE_CHECKING

from storage.cache_common import APP_RECOVERY_REPEATED_BACKUP_UNLOCKED
from trezor import wire
from trezor.enums import MessageType
from trezor.wire import context
from trezor.wire.message_handler import filters, remove_filter

if TYPE_CHECKING:
    from trezor.wire import Handler, Msg


def repeated_backup_enabled() -> bool:
    return context.cache_get_bool(APP_RECOVERY_REPEATED_BACKUP_UNLOCKED)


def activate_repeated_backup() -> None:
    context.cache_set_bool(APP_RECOVERY_REPEATED_BACKUP_UNLOCKED, True)
    filters.append(_repeated_backup_filter)


def deactivate_repeated_backup() -> None:
    context.cache_delete(APP_RECOVERY_REPEATED_BACKUP_UNLOCKED)
    remove_filter(_repeated_backup_filter)


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
