from trezor.crypto import random

if False:
    from typing import Optional

APP_COMMON_SEED = 0
APP_COMMON_SEED_WITHOUT_PASSPHRASE = 1
APP_CARDANO_ROOT = 2
APP_MONERO_LIVE_REFRESH = 3

_cache_session_id = None  # type: Optional[bytes]
_cache = {}

if False:
    from typing import Any


def get_session_id() -> bytes:
    global _cache_session_id
    if not _cache_session_id:
        _cache_session_id = random.bytes(32)
    return _cache_session_id


def set(key: int, value: Any) -> None:
    _cache[key] = value


def get(key: int) -> Any:
    return _cache.get(key)


def clear() -> None:
    global _cache_session_id
    _cache_session_id = None
    _cache.clear()
