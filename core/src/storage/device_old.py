from micropython import const
from typing import TYPE_CHECKING

import storage.cache
from storage import common

if TYPE_CHECKING:
    from typing_extensions import Literal


# Namespace:
_NAMESPACE = common.APP_DEVICE

# fmt: off
# Keys:
DEVICE_ID                  = const(0x00)  # bytes
# MOVE to storage FIDO2
U2F_COUNTER                = const(0x09)  # int
# TODO: move to init
INITIALIZED                = const(0x13)  # bool (0x01 or empty)
# _SAFETY_CHECK_LEVEL        = const(0x14)  # int
_EXPERIMENTAL_FEATURES     = const(0x15)  # bool (0x01 or empty)

SAFETY_CHECK_LEVEL_STRICT  : Literal[0] = const(0)
SAFETY_CHECK_LEVEL_PROMPT  : Literal[1] = const(1)
# fmt: on

# TODO: move to STORAGE_CONSTNAST.PY

HOMESCREEN_MAXSIZE = 16384
LABEL_MAXLENGTH = 32

if __debug__:
    AUTOLOCK_DELAY_MINIMUM = 10 * 1000  # 10 seconds
else:
    AUTOLOCK_DELAY_MINIMUM = 60 * 1000  # 1 minute
AUTOLOCK_DELAY_DEFAULT = 10 * 60 * 1000  # 10 minutes
# autolock intervals larger than AUTOLOCK_DELAY_MAXIMUM cause issues in the scheduler
AUTOLOCK_DELAY_MAXIMUM = 0x2000_0000  # ~6 days

# Length of SD salt auth tag.
# Other SD-salt-related constants are in sd_salt.py
SD_SALT_AUTH_KEY_LEN_BYTES = const(16)


@storage.cache.stored(storage.cache.STORAGE_DEVICE_EXPERIMENTAL_FEATURES)
def _get_experimental_features() -> bytes:
    if common.get_bool(_NAMESPACE, _EXPERIMENTAL_FEATURES):
        return b"\x01"
    else:
        return b""


def get_experimental_features() -> bool:
    return bool(_get_experimental_features())


def set_experimental_features(enabled: bool) -> None:
    cached_bytes = b"\x01" if enabled else b""
    storage.cache.set(storage.cache.STORAGE_DEVICE_EXPERIMENTAL_FEATURES, cached_bytes)
    common.set_true_or_delete(_NAMESPACE, _EXPERIMENTAL_FEATURES, enabled)
