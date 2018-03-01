from trezor.crypto import hashlib, hmac, random
from apps.common import storage

memory = {}
_seed = None
_passphrase = None


def get_state(state: bytes=None, passphrase: str=None):

    if state is None:
        salt = random.bytes(32)  # generate a random salt if no state provided
    else:
        salt = state[:32]        # use salt from provided state

    if passphrase is None:
        global _passphrase
        if _passphrase is None:
            return None
        passphrase = _passphrase    # use cached passphrase

    # state = HMAC(passphrase, salt || device_id)
    msg = salt + storage.get_device_id().encode()
    state = hmac.new(passphrase.encode(), msg, hashlib.sha256).digest()

    return salt + state


def get_seed():
    global _seed
    return _seed


def set_seed(seed, passphrase):
    global _seed, _passphrase
    _seed, _passphrase = seed, passphrase


def has_passphrase():
    global _passphrase
    return _passphrase is not None


def clear():
    global _seed, _passphrase
    _seed, _passphrase = None, None
