from trezor import wire
from trezor.crypto import bip32

from apps.common import HARDENED, cache, storage
from apps.common.request_passphrase import protect_by_passphrase


class Keychain:
    def __init__(self, path: list, root: bip32.HDNode):
        self.path = path
        self.root = root

    def derive(self, node_path: list) -> bip32.HDNode:
        # check we are in the cardano namespace
        prefix = node_path[: len(self.path)]
        suffix = node_path[len(self.path) :]
        if prefix != self.path:
            raise wire.DataError("Forbidden key path")
        # derive child node from the root
        node = self.root.clone()
        for i in suffix:
            node.derive_cardano(i)
        return node


async def get_keychain(ctx: wire.Context) -> Keychain:
    if not storage.is_initialized():
        raise wire.ProcessError("Device is not initialized")

    # derive the root node from mnemonic and passphrase
    passphrase = cache.get_passphrase()
    if passphrase is None:
        passphrase = await protect_by_passphrase(ctx)
        cache.set_passphrase(passphrase)
    root = bip32.from_mnemonic_cardano(storage.get_mnemonic(), passphrase)

    path = [HARDENED | 44, HARDENED | 1815]

    # derive the namespaced root node
    for i in path:
        root.derive_cardano(i)

    keychain = Keychain(path, root)
    return keychain
