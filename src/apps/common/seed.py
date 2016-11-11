from trezor import wire

# FIXME: this is a stub

# TODO: decomplect the MVC layers
# TODO: most likely storage sensitive data in c
# TODO: check pin in constant time
# TODO: pin failure counter

_cached_seed = None
_cached_root_node = None


async def get_node(session_id: int, path: list):
    root = await get_root_node(session_id)
    node = root.clone()
    node.derive_path(path)
    return node


async def get_root_node(session_id: int):
    global _cached_root_node
    if _cached_root_node is None:
        _cached_root_node = await compute_root_node(session_id)
    return _cached_root_node


async def compute_root_node(session_id: int):
    from trezor.crypto import bip32
    seed = await get_seed(session_id)
    return bip32.from_seed(seed, 'secp256k1')


async def get_seed(session_id: int) -> bytes:
    global _cached_seed
    if _cached_seed is None:
        _cached_seed = await compute_seed(session_id)
    return _cached_seed


async def compute_seed(session_id):
    from trezor.crypto import bip39
    from trezor.messages.FailureType import PinInvalid, Other
    from .request_passphrase import request_passphrase
    from .request_pin import request_pin
    from . import storage

    if not storage.is_initialized():
        raise wire.FailureError(Other, 'Device is not initialized')

    if storage.is_protected_by_pin():
        pin = await request_pin(session_id)
        if not storage.check_pin(pin):
            raise wire.FailureError(PinInvalid, 'PIN is incorrect')

    if storage.is_protected_by_passphrase():
        passphrase = await request_passphrase(session_id)
    else:
        passphrase = ''

    return bip39.seed(storage.get_mnemonic(), passphrase)
