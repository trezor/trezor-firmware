from trezor import wire

# FIXME: this is a stub

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
    from trezor.messages.FailureType import Other
    from .request_passphrase import request_passphrase
    from .request_pin import protect_by_pin
    from . import storage

    if not storage.is_initialized():
        raise wire.FailureError(Other, 'Device is not initialized')

    await protect_by_pin(session_id)

    if storage.is_protected_by_passphrase():
        passphrase = await request_passphrase(session_id)
    else:
        passphrase = ''
    return bip39.seed(storage.get_mnemonic(), passphrase)
