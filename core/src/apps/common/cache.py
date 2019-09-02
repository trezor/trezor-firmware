from trezor.crypto import hashlib, hmac, random

from apps.common import storage

if False:
    from typing import Optional

_cached_seed = None  # type: Optional[bytes]
_cached_seed_without_passphrase = None  # type: Optional[bytes]
_cached_passphrase = None  # type: Optional[str]
_cached_passphrase_fprint = b"\x00\x00\x00\x00"  # type: bytes


def get_state(prev_state: bytes = None, passphrase: str = None) -> Optional[bytes]:
    if prev_state is None:
        salt = random.bytes(32)  # generate a random salt if no state provided
    else:
        salt = prev_state[:32]  # use salt from provided state
        if len(salt) != 32:
            return None  # invalid state
    if passphrase is None:
        if _cached_passphrase is None:
            return None  # we don't have any passphrase to compute the state
        else:
            passphrase = _cached_passphrase  # use cached passphrase
    return _compute_state(salt, passphrase)


def _compute_state(salt: bytes, passphrase: str) -> bytes:
    # state = HMAC(passphrase, salt || device_id)
    message = salt + storage.device.get_device_id().encode()
    state = hmac.new(passphrase.encode(), message, hashlib.sha256).digest()
    return salt + state


def get_seed() -> Optional[bytes]:
    return _cached_seed


def get_seed_without_passphrase() -> Optional[bytes]:
    return _cached_seed_without_passphrase


def get_passphrase() -> Optional[str]:
    return _cached_passphrase


def get_passphrase_fprint() -> bytes:
    return _cached_passphrase_fprint


def has_passphrase() -> bool:
    return _cached_passphrase is not None


def set_seed(seed: Optional[bytes]) -> None:
    global _cached_seed
    _cached_seed = seed


def set_seed_without_passphrase(seed: Optional[bytes]) -> None:
    global _cached_seed_without_passphrase
    _cached_seed_without_passphrase = seed


def set_passphrase(passphrase: Optional[str]) -> None:
    global _cached_passphrase, _cached_passphrase_fprint
    _cached_passphrase = passphrase
    _cached_passphrase_fprint = _compute_state(b"FPRINT", passphrase or "")[:4]


def clear(keep_passphrase: bool = False) -> None:
    set_seed(None)
    set_seed_without_passphrase(None)
    if not keep_passphrase:
        set_passphrase(None)
