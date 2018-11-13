from trezor import wire
from trezor.crypto import bip32, bip39

from apps.common import cache, storage
from apps.common.request_passphrase import protect_by_passphrase

_DEFAULT_CURVE = "secp256k1"


class Keychain:
    def __init__(self, seed: bytes):
        self.seed = seed

    def derive(self, path: list, curve_name: str = _DEFAULT_CURVE) -> bip32.HDNode:
        node = bip32.from_seed(self.seed, curve_name)
        node.derive_path(path)
        return node


async def get_keychain(ctx: wire.Context) -> Keychain:
    if not storage.is_initialized():
        # device does not have any seed
        raise wire.ProcessError("Device is not initialized")

    seed = cache.get_seed()
    if seed is None:
        # acquire passphrase
        passphrase = cache.get_passphrase()
        if passphrase is None:
            passphrase = await protect_by_passphrase(ctx)
            cache.set_passphrase(passphrase)

        # compute the seed from mnemonic and passphrase
        seed = bip39.seed(storage.get_mnemonic(), passphrase)
        cache.set_seed(seed)

    keychain = Keychain(seed)
    return keychain


def derive_node_without_passphrase(
    path: list, curve_name: str = _DEFAULT_CURVE
) -> bip32.HDNode:
    if not storage.is_initialized():
        # device does not have any seed
        raise Exception("Device is not initialized")
    seed = bip39.seed(storage.get_mnemonic(), "")
    node = bip32.from_seed(seed, curve_name)
    node.derive_path(path)
    return node


def remove_ed25519_prefix(pubkey: bytes) -> bytes:
    # 0x01 prefix is not part of the actual public key, hence removed
    return pubkey[1:]
