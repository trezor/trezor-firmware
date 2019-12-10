import storage
import storage.cache
from trezor import wire
from trezor.crypto import bip32

from apps.cardano import CURVE, SEED_NAMESPACE
from apps.common import mnemonic
from apps.common.request_passphrase import protect_by_passphrase


class Keychain:
    def __init__(self, path: list, root: bip32.HDNode):
        self.path = path
        self.root = root

    def validate_path(self, checked_path: list, checked_curve: str):
        if checked_curve != CURVE or checked_path[:2] != SEED_NAMESPACE:
            raise wire.DataError("Forbidden key path")

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


async def _get_passphrase(ctx: wire.Context) -> bytes:
    passphrase = storage.cache.get_passphrase()
    if passphrase is None:
        passphrase = await protect_by_passphrase(ctx)
        storage.cache.set_passphrase(passphrase)

    return passphrase


async def get_keychain(ctx: wire.Context) -> Keychain:
    if not storage.is_initialized():
        raise wire.NotInitialized("Device is not initialized")

    if mnemonic.is_bip39():
        # derive the root node from mnemonic and passphrase
        passphrase = await _get_passphrase(ctx)
        root = bip32.from_mnemonic_cardano(mnemonic.get_secret().decode(), passphrase)
    else:
        seed = storage.cache.get_seed()
        if seed is None:
            passphrase = await _get_passphrase(ctx)
            seed = mnemonic.get_seed(passphrase)
            storage.cache.set_seed(seed)
        root = bip32.from_seed(seed, "ed25519 cardano seed")

    # derive the namespaced root node
    for i in SEED_NAMESPACE:
        root.derive_cardano(i)

    keychain = Keychain(SEED_NAMESPACE, root)
    return keychain
