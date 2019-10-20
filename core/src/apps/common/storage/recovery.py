from micropython import const

from apps.common.storage import common, recovery_shares

# Namespace:
_NAMESPACE = common._APP_RECOVERY

# fmt: off
# Keys:
_IN_PROGRESS               = const(0x00)  # bool
_DRY_RUN                   = const(0x01)  # bool
_WORD_COUNT                = const(0x02)  # int
_REMAINING                 = const(0x05)  # int
_SLIP39_IDENTIFIER         = const(0x03)  # bytes
_SLIP39_THRESHOLD          = const(0x04)  # int
_SLIP39_ITERATION_EXPONENT = const(0x06)  # int
# fmt: on

if False:
    from typing import Optional


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


def set_slip39_identifier(identifier: int) -> None:
    common._set_uint16(_NAMESPACE, _SLIP39_IDENTIFIER, identifier)


def get_slip39_identifier() -> Optional[int]:
    return common._get_uint16(_NAMESPACE, _SLIP39_IDENTIFIER)


def set_slip39_threshold(threshold: int) -> None:
    common._set_uint8(_NAMESPACE, _SLIP39_THRESHOLD, threshold)


def get_slip39_threshold() -> Optional[int]:
    return common._get_uint8(_NAMESPACE, _SLIP39_THRESHOLD)


def set_remaining(remaining: int) -> None:
    common._set_uint8(_NAMESPACE, _REMAINING, remaining)


def get_remaining() -> Optional[int]:
    return common._get_uint8(_NAMESPACE, _REMAINING)


def set_slip39_iteration_exponent(exponent: int) -> None:
    common._set_uint8(_NAMESPACE, _SLIP39_ITERATION_EXPONENT, exponent)


def get_slip39_iteration_exponent() -> Optional[int]:
    return common._get_uint8(_NAMESPACE, _SLIP39_ITERATION_EXPONENT)


def end_progress() -> None:
    common._delete(_NAMESPACE, _IN_PROGRESS)
    common._delete(_NAMESPACE, _DRY_RUN)
    common._delete(_NAMESPACE, _WORD_COUNT)
    common._delete(_NAMESPACE, _SLIP39_IDENTIFIER)
    common._delete(_NAMESPACE, _SLIP39_THRESHOLD)
    common._delete(_NAMESPACE, _REMAINING)
    common._delete(_NAMESPACE, _SLIP39_ITERATION_EXPONENT)
    recovery_shares.delete()
