from trezor import wire
from trezor.crypto import bip32
from trezor.wire import errors

from apps.cardano import CURVE, SEED_NAMESPACE
from apps.common import cache, mnemonic, storage
from apps.common.request_passphrase import protect_by_passphrase


class Keychain:
    def __init__(self, path: list, root: bip32.HDNode):
        self.path = path
        self.root = root

    def validate_path(self, checked_path: list, checked_curve: str):
        if checked_curve != CURVE or checked_path[:2] != SEED_NAMESPACE:
            raise errors.DataError("Forbidden key path")

    def derive(self, node_path: list) -> bip32.HDNode:
        # check we are in the cardano namespace
        prefix = node_path[: len(self.path)]
        suffix = node_path[len(self.path) :]
        if prefix != self.path:
            raise errors.DataError("Forbidden key path")
        # derive child node from the root
        node = self.root.clone()
        for i in suffix:
            node.derive_cardano(i)
        return node


async def get_keychain(ctx: wire.Context) -> Keychain:
    if not storage.is_initialized():
        raise errors.ProcessError("Device is not initialized")

    # derive the root node from mnemonic and passphrase
    passphrase = cache.get_passphrase()
    if passphrase is None:
        passphrase = await protect_by_passphrase(ctx)
        cache.set_passphrase(passphrase)
    root = bip32.from_mnemonic_cardano(mnemonic.restore(), passphrase)

    # derive the namespaced root node
    for i in SEED_NAMESPACE:
        root.derive_cardano(i)

    keychain = Keychain(SEED_NAMESPACE, root)
    return keychain
