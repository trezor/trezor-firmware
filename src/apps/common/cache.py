_seed, _state = None, None


def get_state():
    global _state
    return _state


def get_seed():
    global _seed
    return _seed


def set_seed(seed):
    from trezor.crypto import bip32
    from trezor.crypto.hashlib import blake2s
    node = bip32.from_seed(seed, 'secp256k1')
    state = blake2s(node.public_key()).digest()
    global _seed, _state
    _seed, _state = seed, state


def clear():
    global _seed, _state
    _seed, _state = None, None
