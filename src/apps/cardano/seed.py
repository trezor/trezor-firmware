from trezor import wire
from trezor.crypto import bip32

from apps.common import HARDENED, cache, storage
from apps.common.request_passphrase import protect_by_passphrase


class Keychain:
    def __init__(self, root: bip32.HDNode):
        self.root = root

    def derive(self, path: list) -> bip32.HDNode:
        self.validate_path(path)
        node = self.root.clone()
        for i in path:
            node.derive_cardano(i)
        return node

    def validate_path(self, path: list) -> None:
        if len(path) < 2 or len(path) > 5:
            raise wire.ProcessError("Derivation path must be composed from 2-5 indices")
        if path[0] != HARDENED | 44 or path[1] != HARDENED | 1815:
            raise wire.ProcessError("This is not cardano derivation path")


async def get_keychain(ctx: wire.Context) -> Keychain:
    if not storage.is_initialized():
        # device does not have any seed
        raise wire.ProcessError("Device is not initialized")

    # acquire passphrase
    passphrase = cache.get_passphrase()
    if passphrase is None:
        passphrase = await protect_by_passphrase(ctx)
        cache.set_passphrase(passphrase)

    # compute the seed from mnemonic and passphrase
    root = bip32.from_mnemonic_cardano(storage.get_mnemonic(), passphrase)

    keychain = Keychain(root)
    return keychain
