from trezor import wire
from trezor.crypto import bip32
from trezor.crypto import bip39

_DEFAULT_CURVE = 'secp256k1'

_cached_seed = None


async def get_root(session_id: int, curve_name=_DEFAULT_CURVE):
    seed = await get_seed(session_id)
    root = bip32.from_seed(seed, curve_name)
    return root


async def get_seed(session_id: int) -> bytes:
    global _cached_seed
    if _cached_seed is None:
        _cached_seed = await compute_seed(session_id)
    return _cached_seed


async def compute_seed(session_id: int) -> bytes:
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
