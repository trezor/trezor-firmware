from trezor import wire
from trezor.crypto import bip32
from trezor.crypto import bip39

_DEFAULT_CURVE = 'secp256k1'


async def derive_node(ctx: wire.Context, path=[], curve_name=_DEFAULT_CURVE):
    seed = await _get_seed(ctx)
    node = bip32.from_seed(seed, curve_name)
    if len(path) > 0:
        node.derive_path(path)
    return node


async def _get_seed(ctx: wire.Context) -> bytes:
    from . import cache
    if cache.get_seed() is None:
        seed = await _compute_seed(ctx)
        cache.set_seed(seed)
    return cache.get_seed()


async def _compute_seed(ctx: wire.Context) -> bytes:
    from trezor.messages.FailureType import ProcessError
    from .request_passphrase import protect_by_passphrase
    from . import storage

    if not storage.is_initialized():
        raise wire.FailureError(ProcessError, 'Device is not initialized')

    passphrase = await protect_by_passphrase(ctx)
    return bip39.seed(storage.get_mnemonic(), passphrase)


def derive_node_without_passphrase(path, curve_name=_DEFAULT_CURVE):
    from . import storage
    if not storage.is_initialized():
        raise Exception('Device is not initialized')
    seed = bip39.seed(storage.get_mnemonic(), '')
    node = bip32.from_seed(seed, curve_name)
    node.derive_path(path)
    return node
