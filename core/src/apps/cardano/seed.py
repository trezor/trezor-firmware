import storage
from storage import cache
from trezor import wire
from trezor.crypto import bip32

from apps.cardano import BYRON_SEED_NAMESPACE, SHELLEY_SEED_NAMESPACE
from apps.common import mnemonic
from apps.common.passphrase import get as get_passphrase

if False:
    from typing import Tuple

    from apps.common.seed import Bip32Path, MsgIn, MsgOut, Handler, HandlerWithKeychain


class Keychain:
    """Cardano keychain hard-coded to SEED_NAMESPACE."""

    def __init__(self, root: bip32.HDNode) -> None:
        self.root = root

    def match_path(self, path: Bip32Path) -> Tuple[int, Bip32Path]:
        namespace_length = len(SHELLEY_SEED_NAMESPACE)
        if (
            path[:namespace_length] != SHELLEY_SEED_NAMESPACE
            and path[:namespace_length] != BYRON_SEED_NAMESPACE
        ):
            raise wire.DataError("Forbidden key path")

        return 0, path[namespace_length:]

    def derive(self, node_path: Bip32Path) -> bip32.HDNode:
        _, suffix = self.match_path(node_path)
        # derive child node from the root
        node = self.root.clone()
        for i in suffix:
            node.derive_cardano(i)
        return node

    # XXX the root node remains in session cache so we should not delete it
    # def __del__(self) -> None:
    #     self.root.__del__()


class Keychains:
    def __init__(self, byron_keychain: Keychain, shelley_keychain: Keychain):
        self.byron_keychain = byron_keychain
        self.shelley_keychain = shelley_keychain

    def _get_keychain(self, namespace: list) -> Keychain:
        if namespace == BYRON_SEED_NAMESPACE:
            return self.byron_keychain
        elif namespace == SHELLEY_SEED_NAMESPACE:
            return self.shelley_keychain
        else:
            raise wire.DataError("Invalid namespace")

    def match_path(self, checked_path: list) -> None:
        keychain = self._get_keychain(checked_path[:2])
        keychain.match_path(checked_path)

    def derive(self, node_path: list) -> bip32.HDNode:
        keychain = self._get_keychain(node_path[:2])
        return keychain.derive(node_path)


@cache.stored_async(cache.APP_CARDANO_ROOT)
async def get_keychains(ctx: wire.Context) -> Keychain:
    byron_keychain = await _get_keychain(ctx, BYRON_SEED_NAMESPACE)
    shelley_keychain = await _get_keychain(ctx, SHELLEY_SEED_NAMESPACE)

    return Keychains(byron_keychain, shelley_keychain)


async def _get_keychain(ctx: wire.Context, namespace) -> Keychain:
    if not storage.is_initialized():
        raise wire.NotInitialized("Device is not initialized")

    passphrase = await get_passphrase(ctx)
    if mnemonic.is_bip39():
        # derive the root node from mnemonic and passphrase via Cardano Icarus algorithm
        root = bip32.from_mnemonic_cardano(mnemonic.get_secret().decode(), passphrase)
    else:
        # derive the root node via SLIP-0023
        seed = mnemonic.get_seed(passphrase)
        root = bip32.from_seed(seed, "ed25519 cardano seed")

    # derive the namespaced root node
    for i in namespace:
        root.derive_cardano(i)

    keychain = Keychain(root)
    return keychain


def with_keychains(func: HandlerWithKeychain[MsgIn, MsgOut]) -> Handler[MsgIn, MsgOut]:
    async def wrapper(ctx: wire.Context, msg: MsgIn) -> MsgOut:
        keychains = await get_keychains(ctx)
        return await func(ctx, msg, keychains)

    return wrapper
