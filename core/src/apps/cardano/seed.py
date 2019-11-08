import storage
from trezor import wire
from trezor.crypto import bip32

from apps.cardano import CURVE, SEED_NAMESPACE
from apps.common import mnemonic
from apps.common.passphrase import get as get_passphrase

if False:
    from typing import Optional

_cached_root = None  # type: Optional[bytes]


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


async def get_keychain(ctx: wire.Context) -> Keychain:
    global _cached_root

    if not storage.is_initialized():
        raise wire.NotInitialized("Device is not initialized")

    if _cached_root is None:
        passphrase = await get_passphrase(ctx)
        if mnemonic.is_bip39():
            # derive the root node from mnemonic and passphrase
            _cached_root = bip32.from_mnemonic_cardano(
                mnemonic.get_secret().decode(), passphrase
            )
        else:
            seed = mnemonic.get_seed(passphrase)
            _cached_root = bip32.from_seed(seed, "ed25519 cardano seed")

    # derive the namespaced root node
    for i in SEED_NAMESPACE:
        _cached_root.derive_cardano(i)

    keychain = Keychain(SEED_NAMESPACE, _cached_root)
    return keychain
