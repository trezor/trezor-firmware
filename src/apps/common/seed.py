from trezor import wire
from trezor.crypto import bip32, bip39
from apps.common import cache, storage
from apps.common.request_passphrase import protect_by_passphrase

_DEFAULT_CURVE = 'secp256k1'


async def derive_node(ctx: wire.Context, path: list, curve_name=_DEFAULT_CURVE):
    seed = await _get_cached_seed(ctx)
    node = bip32.from_seed(seed, curve_name)
    if path:
        node.derive_path(path)
    return node


async def _get_cached_seed(ctx: wire.Context) -> bytes:
    if not storage.is_initialized():
        raise wire.ProcessError('Device is not initialized')
    if cache.get_seed() is None:
        passphrase = await _get_cached_passphrase(ctx)
        seed = bip39.seed(storage.get_mnemonic(), passphrase)
        cache.set_seed(seed)
    return cache.get_seed()


async def _get_cached_passphrase(ctx: wire.Context) -> str:
    if cache.get_passphrase() is None:
        passphrase = await protect_by_passphrase(ctx)
        cache.set_passphrase(passphrase)
    return cache.get_passphrase()


def derive_node_without_passphrase(path, curve_name=_DEFAULT_CURVE):
    if not storage.is_initialized():
        raise Exception('Device is not initialized')

    seed = bip39.seed(storage.get_mnemonic(), '')
    node = bip32.from_seed(seed, curve_name)
    node.derive_path(path)
    return node
