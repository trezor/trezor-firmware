from trezor.crypto import hashlib, hmac, random
from apps.common import storage

memory = {}
_seed = None
_passphrase = None
_state_salt = None


def get_state(salt: bytes=None, passphrase: str=None):
    global _passphrase, _state_salt
    if salt is None:
        # generate a random salt if not provided and not already cached
        if _state_salt is None:
            _state_salt = random.bytes(32)
    else:
        # otherwise copy provided salt to cached salt
        _state_salt = salt

    # state = HMAC(passphrase, salt || device_id)
    if passphrase is None:
        key = _passphrase if _passphrase is not None else ''
    else:
        key = passphrase
    msg = _state_salt + storage.get_device_id().encode()
    state = hmac.new(key.encode(), msg, hashlib.sha256).digest()

    return _state_salt + state


def get_seed():
    global _seed
    return _seed


def set_seed(seed, passphrase):
    global _seed, _passphrase
    _seed, _passphrase = seed, _passphrase


def has_passphrase():
    global _passphrase
    return _passphrase is not None


def clear():
    global _seed, _passphrase
    global _state_salt
    _seed, _passphrase = None, None
    _state_salt = None
