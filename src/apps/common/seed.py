from trezor import wire
from trezor.crypto import bip32, bip39
from trezor.messages.FailureType import ProcessError
from apps.common import cache, storage
from apps.common.request_passphrase import protect_by_passphrase

_DEFAULT_CURVE = 'secp256k1'


async def derive_node(ctx: wire.Context, path=(), curve_name=_DEFAULT_CURVE):
    seed = await _get_seed(ctx)
    node = bip32.from_seed(seed, curve_name)
    if path:
        node.derive_path(path)
    return node


async def _get_seed(ctx: wire.Context) -> bytes:
    if cache.get_seed() is None:
        seed, passphrase = await _compute_seed(ctx)
        cache.set_seed(seed, passphrase)
    return cache.get_seed()


async def _compute_seed(ctx: wire.Context) -> (bytes, str):
    if not storage.is_initialized():
        raise wire.FailureError(ProcessError, 'Device is not initialized')

    passphrase = await protect_by_passphrase(ctx)
    return bip39.seed(storage.get_mnemonic(), passphrase), passphrase


def derive_node_without_passphrase(path, curve_name=_DEFAULT_CURVE):
    if not storage.is_initialized():
        raise Exception('Device is not initialized')

    seed = bip39.seed(storage.get_mnemonic(), '')
    node = bip32.from_seed(seed, curve_name)
    node.derive_path(path)
    return node
