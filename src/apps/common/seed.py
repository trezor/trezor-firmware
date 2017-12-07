from trezor import wire
from trezor.crypto import bip32
from trezor.crypto import bip39

_DEFAULT_CURVE = 'secp256k1'


async def get_root(ctx: wire.Context, curve_name=_DEFAULT_CURVE):
    seed = await get_seed(ctx)
    root = bip32.from_seed(seed, curve_name)
    return root


async def get_seed(ctx: wire.Context) -> bytes:
    from . import cache
    if cache.seed is None:
        cache.seed = await compute_seed(ctx)
    return cache.seed


async def compute_seed(ctx: wire.Context) -> bytes:
    from trezor.messages.FailureType import ProcessError
    from .request_passphrase import protect_by_passphrase
    from . import storage

    if not storage.is_initialized():
        raise wire.FailureError(ProcessError, 'Device is not initialized')

    passphrase = await protect_by_passphrase(ctx)
    return bip39.seed(storage.get_mnemonic(), passphrase)


def get_root_without_passphrase(curve_name=_DEFAULT_CURVE):
    from . import storage
    if not storage.is_initialized():
        raise Exception('Device is not initialized')
    seed = bip39.seed(storage.get_mnemonic(), '')
    root = bip32.from_seed(seed, curve_name)
    return root
