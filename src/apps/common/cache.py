seed = None


def get_state():
    global seed
    if seed is None:
        return None
    else:
        from trezor.crypto import bip32
        from trezor.crypto.hashlib import blake2s
        node = bip32.from_seed(seed, 'secp256k1')
        state = blake2s(node.public_key()).digest()
        return state


def clear():
    global seed
    seed = None
