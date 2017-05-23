from trezor import wire
from trezor.crypto import bip32
from trezor.crypto import bip39

_DEFAULT_CURVE = 'secp256k1'


async def get_root(session_id: int, curve_name=_DEFAULT_CURVE):
    seed = await get_seed(session_id)
    root = bip32.from_seed(seed, curve_name)
    return root


async def get_seed(session_id: int) -> bytes:
    from . import cache
    if cache.seed is None:
        cache.seed = await compute_seed(session_id)
    return cache.seed


async def compute_seed(session_id: int) -> bytes:
    from trezor.messages.FailureType import Other
    from .request_passphrase import protect_by_passphrase
    from .request_pin import protect_by_pin
    from . import storage

    if not storage.is_initialized():
        raise wire.FailureError(Other, 'Device is not initialized')

    await protect_by_pin(session_id)

    passphrase = await protect_by_passphrase(session_id)
    return bip39.seed(storage.get_mnemonic(), passphrase)


def get_root_without_passphrase(curve_name=_DEFAULT_CURVE):
    from . import storage
    if not storage.is_initialized():
        raise Exception('Device is not initialized')
    if storage.is_locked():
        raise Exception('Unlock first')
    seed = bip39.seed(storage.get_mnemonic(), '')
    root = bip32.from_seed(seed, curve_name)
    return root
