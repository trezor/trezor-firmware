from storage import cache, device
from trezor import wire
from trezor.crypto import bip32

from apps.common import mnemonic
from apps.common.passphrase import get as get_passphrase
from apps.common.seed import get_seed

from .helpers import paths

if False:
    from typing import Callable, Awaitable

    from apps.common.paths import Bip32Path
    from apps.common.keychain import MsgIn, MsgOut, Handler

    HandlerWithKeychain = Callable[[wire.Context, MsgIn, "Keychain"], Awaitable[MsgOut]]


class Keychain:
    """
    Cardano keychain hard-coded to 44 (Byron), 1852 (Shelley), 1854 (multi-sig) and 1855 (token minting)
    seed namespaces.
    """

    def __init__(self, root: bip32.HDNode) -> None:
        self.byron_root = derive_path_cardano(root, paths.BYRON_ROOT)
        self.shelley_root = derive_path_cardano(root, paths.SHELLEY_ROOT)
        self.multisig_root = derive_path_cardano(root, paths.MULTISIG_ROOT)
        self.minting_root = derive_path_cardano(root, paths.MINTING_ROOT)
        root.__del__()

    def verify_path(self, path: Bip32Path) -> None:
        if not self.is_in_keychain(path):
            raise wire.DataError("Forbidden key path")

    def _get_path_root(self, path: Bip32Path) -> bip32.HDNode:
        if is_byron_path(path):
            return self.byron_root
        elif is_shelley_path(path):
            return self.shelley_root
        elif is_multisig_path(path):
            return self.multisig_root
        elif is_minting_path(path):
            return self.minting_root
        else:
            raise wire.DataError("Forbidden key path")

    def is_in_keychain(self, path: Bip32Path) -> bool:
        return (
            is_byron_path(path)
            or is_shelley_path(path)
            or is_multisig_path(path)
            or is_minting_path(path)
        )

    def derive(self, node_path: Bip32Path) -> bip32.HDNode:
        self.verify_path(node_path)
        path_root = self._get_path_root(node_path)

        # this is true now, so for simplicity we don't branch on path type
        assert (
            len(paths.BYRON_ROOT) == len(paths.SHELLEY_ROOT)
            and len(paths.MULTISIG_ROOT) == len(paths.SHELLEY_ROOT)
            and len(paths.MINTING_ROOT) == len(paths.SHELLEY_ROOT)
        )
        suffix = node_path[len(paths.SHELLEY_ROOT) :]

        # derive child node from the root
        return derive_path_cardano(path_root, suffix)

    # XXX the root node remains in session cache so we should not delete it
    # def __del__(self) -> None:
    #     self.root.__del__()


def is_byron_path(path: Bip32Path) -> bool:
    return path[: len(paths.BYRON_ROOT)] == paths.BYRON_ROOT


def is_shelley_path(path: Bip32Path) -> bool:
    return path[: len(paths.SHELLEY_ROOT)] == paths.SHELLEY_ROOT


def is_multisig_path(path: Bip32Path) -> bool:
    return path[: len(paths.MULTISIG_ROOT)] == paths.MULTISIG_ROOT


def is_minting_path(path: Bip32Path) -> bool:
    return path[: len(paths.MINTING_ROOT)] == paths.MINTING_ROOT


def derive_path_cardano(root: bip32.HDNode, path: Bip32Path) -> bip32.HDNode:
    node = root.clone()
    for i in path:
        node.derive_cardano(i)
    return node


@cache.stored_async(cache.APP_CARDANO_PASSPHRASE)
async def _get_passphrase(ctx: wire.Context) -> bytes:
    return (await get_passphrase(ctx)).encode()


async def _get_keychain_bip39(ctx: wire.Context) -> Keychain:
    if not device.is_initialized():
        raise wire.NotInitialized("Device is not initialized")

    # ask for passphrase, loading from cache if necessary
    passphrase = await _get_passphrase(ctx)
    # derive the root node from mnemonic and passphrase via Cardano Icarus algorithm
    secret_bytes = mnemonic.get_secret()
    assert secret_bytes is not None
    root = bip32.from_mnemonic_cardano(secret_bytes.decode(), passphrase.decode())
    return Keychain(root)


async def get_keychain(ctx: wire.Context) -> Keychain:
    if mnemonic.is_bip39():
        return await _get_keychain_bip39(ctx)
    else:
        # derive the root node via SLIP-0023 https://github.com/satoshilabs/slips/blob/master/slip-0022.md
        seed = await get_seed(ctx)
        return Keychain(bip32.from_seed(seed, "ed25519 cardano seed"))


def with_keychain(func: HandlerWithKeychain[MsgIn, MsgOut]) -> Handler[MsgIn, MsgOut]:
    async def wrapper(ctx: wire.Context, msg: MsgIn) -> MsgOut:
        keychain = await get_keychain(ctx)
        return await func(ctx, msg, keychain)

    return wrapper
