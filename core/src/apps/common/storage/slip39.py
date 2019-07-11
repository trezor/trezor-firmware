from micropython import const

from apps.common.storage import common, slip39_mnemonics

if False:
    from typing import Optional

# Namespace:
_NAMESPACE = common._APP_SLIP39

# fmt: off
# Keys:
_SLIP39_IDENTIFIER         = const(0x01)  # bytes
_SLIP39_THRESHOLD          = const(0x02)  # int
_SLIP39_REMAINING          = const(0x03)  # int
_SLIP39_ITERATION_EXPONENT = const(0x05)  # int
# fmt: on


def set_identifier(identifier: int) -> None:
    common._set_uint16(_NAMESPACE, _SLIP39_IDENTIFIER, identifier)


def get_identifier() -> Optional[int]:
    return common._get_uint16(_NAMESPACE, _SLIP39_IDENTIFIER)


def set_threshold(threshold: int) -> None:
    common._set_uint8(_NAMESPACE, _SLIP39_THRESHOLD, threshold)


def get_threshold() -> Optional[int]:
    return common._get_uint8(_NAMESPACE, _SLIP39_THRESHOLD)


def set_remaining(remaining: int) -> None:
    common._set_uint8(_NAMESPACE, _SLIP39_REMAINING, remaining)


def get_remaining() -> Optional[int]:
    return common._get_uint8(_NAMESPACE, _SLIP39_REMAINING)


def set_iteration_exponent(exponent: int) -> None:
    common._set_uint8(_NAMESPACE, _SLIP39_ITERATION_EXPONENT, exponent)


def get_iteration_exponent() -> Optional[int]:
    return common._get_uint8(_NAMESPACE, _SLIP39_ITERATION_EXPONENT)


def _delete_progress() -> None:
    common._delete(_NAMESPACE, _SLIP39_REMAINING)
    common._delete(_NAMESPACE, _SLIP39_THRESHOLD)
    slip39_mnemonics.delete()
