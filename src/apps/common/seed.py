from trezor import wire
from trezor.crypto import bip32, bip39

from apps.common import cache, storage
from apps.common.request_passphrase import protect_by_passphrase

allow = list


class Keychain:
    """
    Keychain provides an API for deriving HD keys from previously allowed
    key-spaces.
    """

    def __init__(self, paths: list, roots: list):
        self.paths = paths
        self.roots = roots

    def derive(self, node_path: list, curve_name: str = "secp256k1") -> bip32.HDNode:
        # find the root node
        root_index = 0
        for curve, *path in self.paths:
            prefix = node_path[: len(path)]
            suffix = node_path[len(path) :]
            if curve == curve_name and path == prefix:
                break
            root_index += 1
        else:
            raise wire.DataError("Forbidden key path")
        # derive child node from the root
        node = self.roots[root_index].clone()
        node.derive_path(suffix)
        return node


async def get_keychain(ctx: wire.Context, paths: list) -> Keychain:
    if not storage.is_initialized():
        raise wire.ProcessError("Device is not initialized")

    seed = cache.get_seed()
    if seed is None:
        # derive seed from mnemonic and passphrase
        passphrase = cache.get_passphrase()
        if passphrase is None:
            passphrase = await protect_by_passphrase(ctx)
            cache.set_passphrase(passphrase)
        seed = bip39.seed(storage.get_mnemonic(), passphrase)
        cache.set_seed(seed)

    # derive namespaced root nodes
    roots = []
    for curve, *path in paths:
        node = bip32.from_seed(seed, curve)
        node.derive_path(path)
        roots.append(node)

    keychain = Keychain(paths, roots)
    return keychain


def derive_node_without_passphrase(
    path: list, curve_name: str = "secp256k1"
) -> bip32.HDNode:
    if not storage.is_initialized():
        raise Exception("Device is not initialized")
    seed = bip39.seed(storage.get_mnemonic(), "")
    node = bip32.from_seed(seed, curve_name)
    node.derive_path(path)
    return node


def remove_ed25519_prefix(pubkey: bytes) -> bytes:
    # 0x01 prefix is not part of the actual public key, hence removed
    return pubkey[1:]
