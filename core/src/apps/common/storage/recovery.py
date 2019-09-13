from micropython import const

from trezor.crypto import slip39

from apps.common.storage import common, recovery_shares

if False:
    from apps.management.recovery_device.backup_types import BackupTypeUnion

# Namespace:
_NAMESPACE = common._APP_RECOVERY

# fmt: off
# Keys:
_IN_PROGRESS               = const(0x00)  # bool
_DRY_RUN                   = const(0x01)  # bool
_WORD_COUNT                = const(0x02)  # int
_SLIP39_IDENTIFIER         = const(0x03)  # bytes
_SLIP39_THRESHOLD          = const(0x04)  # int
_REMAINING                 = const(0x05)  # int
_SLIP39_ITERATION_EXPONENT = const(0x06)  # int
_SLIP39_GROUP_COUNT        = const(0x07)  # int
_SLIP39_GROUP_THRESHOLD    = const(0x08)  # int
_BACKUP_TYPE               = const(0x09)  # int
# fmt: on

if False:
    from typing import List, Optional


def set_in_progress(val: bool) -> None:
    common._set_bool(_NAMESPACE, _IN_PROGRESS, val)


def is_in_progress() -> bool:
    return common._get_bool(_NAMESPACE, _IN_PROGRESS)


def set_dry_run(val: bool) -> None:
    common._set_bool(_NAMESPACE, _DRY_RUN, val)


def is_dry_run() -> bool:
    return common._get_bool(_NAMESPACE, _DRY_RUN)


def set_word_count(count: int) -> None:
    common._set_uint8(_NAMESPACE, _WORD_COUNT, count)


def get_word_count() -> Optional[int]:
    return common._get_uint8(_NAMESPACE, _WORD_COUNT)


def set_backup_type(backup_type: BackupTypeUnion) -> None:
    common._set_uint8(_NAMESPACE, _BACKUP_TYPE, backup_type)


def get_backup_type() -> Optional[BackupTypeUnion]:
    return common._get_uint8(_NAMESPACE, _BACKUP_TYPE)


def set_slip39_identifier(identifier: int) -> None:
    common._set_uint16(_NAMESPACE, _SLIP39_IDENTIFIER, identifier)


def get_slip39_identifier() -> Optional[int]:
    return common._get_uint16(_NAMESPACE, _SLIP39_IDENTIFIER)


def set_slip39_threshold(threshold: int) -> None:
    common._set_uint8(_NAMESPACE, _SLIP39_THRESHOLD, threshold)


def get_slip39_threshold() -> Optional[int]:
    return common._get_uint8(_NAMESPACE, _SLIP39_THRESHOLD)


def set_slip39_iteration_exponent(exponent: int) -> None:
    common._set_uint8(_NAMESPACE, _SLIP39_ITERATION_EXPONENT, exponent)


def get_slip39_iteration_exponent() -> Optional[int]:
    return common._get_uint8(_NAMESPACE, _SLIP39_ITERATION_EXPONENT)


def set_slip39_group_count(group_count: int) -> None:
    common._set_uint8(_NAMESPACE, _SLIP39_GROUP_COUNT, group_count)


def get_slip39_group_count() -> Optional[int]:
    return common._get_uint8(_NAMESPACE, _SLIP39_GROUP_COUNT)


def set_slip39_group_threshold(group_threshold: int) -> None:
    common._set_uint8(_NAMESPACE, _SLIP39_GROUP_THRESHOLD, group_threshold)


def get_slip39_group_threshold() -> Optional[int]:
    return common._get_uint8(_NAMESPACE, _SLIP39_GROUP_THRESHOLD)


def set_slip39_remaining_shares(shares_remaining: int, group_index: int = 0) -> None:
    """
    We store the remaining shares as a bytearray of length group_count.
    Each byte represents share remaining for group of that group_index.
    0x10 (16) was chosen as the default value because it's the max
    share count for a group.
    """
    remaining = common._get(_NAMESPACE, _REMAINING)
    group_count = get_slip39_group_count()
    if not group_count:
        raise RuntimeError
    if remaining is None:
        remaining = bytearray([slip39.MAX_SHARE_COUNT] * group_count)
    remaining = bytearray(remaining)
    remaining[group_index] = shares_remaining
    common._set(_NAMESPACE, _REMAINING, remaining)


def get_slip39_remaining_shares(group_index: int = 0) -> Optional[int]:
    remaining = common._get(_NAMESPACE, _REMAINING)
    if remaining is None or remaining[group_index] == slip39.MAX_SHARE_COUNT:
        return None
    else:
        return remaining[group_index]


def fetch_slip39_remaining_shares() -> Optional[List[int]]:
    remaining = common._get(_NAMESPACE, _REMAINING)
    if not remaining:
        return None

    result = []
    for i in range(get_slip39_group_count()):
        result.append(remaining[i])

    return result


def end_progress() -> None:
    common._delete(_NAMESPACE, _IN_PROGRESS)
    common._delete(_NAMESPACE, _DRY_RUN)
    common._delete(_NAMESPACE, _WORD_COUNT)
    common._delete(_NAMESPACE, _SLIP39_IDENTIFIER)
    common._delete(_NAMESPACE, _SLIP39_THRESHOLD)
    common._delete(_NAMESPACE, _REMAINING)
    common._delete(_NAMESPACE, _SLIP39_ITERATION_EXPONENT)
    common._delete(_NAMESPACE, _SLIP39_GROUP_COUNT)
    common._delete(_NAMESPACE, _SLIP39_GROUP_THRESHOLD)
    common._delete(_NAMESPACE, _BACKUP_TYPE)
    recovery_shares.delete()
