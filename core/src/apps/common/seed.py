from typing import TYPE_CHECKING

import storage.cache as storage_cache
import storage.device as storage_device
from trezor import utils
from trezor.crypto import hmac

from . import mnemonic
from .passphrase import get as get_passphrase

if TYPE_CHECKING:
    from .paths import Bip32Path, Slip21Path
    from trezor.wire import Context
    from trezor.crypto import bip32


class Slip21Node:
    """
    This class implements the SLIP-0021 hierarchical derivation of symmetric keys, see
    https://github.com/satoshilabs/slips/blob/master/slip-0021.md.
    """

    def __init__(self, seed: bytes | None = None, data: bytes | None = None) -> None:
        assert seed is None or data is None, "Specify exactly one of: seed, data"
        if data is not None:
            self.data = data
        elif seed is not None:
            self.data = hmac(hmac.SHA512, b"Symmetric key seed", seed).digest()
        else:
            raise ValueError  # neither seed nor data specified

    def __del__(self) -> None:
        del self.data

    def derive_path(self, path: Slip21Path) -> None:
        for label in path:
            h = hmac(hmac.SHA512, self.data[0:32], b"\x00")
            h.update(label)
            self.data = h.digest()

    def key(self) -> bytes:
        return self.data[32:64]

    def clone(self) -> "Slip21Node":
        return Slip21Node(data=self.data)


if not utils.BITCOIN_ONLY:
    # === Cardano variant ===
    # We want to derive both the normal seed and the Cardano seed together, AND
    # expose a method for Cardano to do the same

    async def derive_and_store_roots(ctx: Context) -> None:
        from trezor import wire

        if not storage_device.is_initialized():
            raise wire.NotInitialized("Device is not initialized")

        need_seed = not storage_cache.is_set(storage_cache.APP_COMMON_SEED)
        need_cardano_secret = storage_cache.get(
            storage_cache.APP_COMMON_DERIVE_CARDANO
        ) and not storage_cache.is_set(storage_cache.APP_CARDANO_ICARUS_SECRET)

        if not need_seed and not need_cardano_secret:
            return

        passphrase = await get_passphrase(ctx)

        if need_seed:
            common_seed = mnemonic.get_seed(passphrase)
            storage_cache.set(storage_cache.APP_COMMON_SEED, common_seed)

        if need_cardano_secret:
            from apps.cardano.seed import derive_and_store_secrets

            derive_and_store_secrets(passphrase)

    @storage_cache.stored_async(storage_cache.APP_COMMON_SEED)
    async def get_seed(ctx: Context) -> bytes:
        await derive_and_store_roots(ctx)
        common_seed = storage_cache.get(storage_cache.APP_COMMON_SEED)
        assert common_seed is not None
        return common_seed

else:
    # === Bitcoin-only variant ===
    # We use the simple version of `get_seed` that never needs to derive anything else.

    @storage_cache.stored_async(storage_cache.APP_COMMON_SEED)
    async def get_seed(ctx: Context) -> bytes:
        passphrase = await get_passphrase(ctx)
        return mnemonic.get_seed(passphrase)


@storage_cache.stored(storage_cache.APP_COMMON_SEED_WITHOUT_PASSPHRASE)
def _get_seed_without_passphrase() -> bytes:
    if not storage_device.is_initialized():
        raise Exception("Device is not initialized")
    return mnemonic.get_seed(progress_bar=False)


def derive_node_without_passphrase(
    path: Bip32Path, curve_name: str = "secp256k1"
) -> bip32.HDNode:
    from trezor.crypto import bip32

    seed = _get_seed_without_passphrase()
    node = bip32.from_seed(seed, curve_name)
    node.derive_path(path)
    return node


def derive_slip21_node_without_passphrase(path: Slip21Path) -> Slip21Node:
    seed = _get_seed_without_passphrase()
    node = Slip21Node(seed)
    node.derive_path(path)
    return node


def remove_ed25519_prefix(pubkey: bytes) -> bytes:
    # 0x01 prefix is not part of the actual public key, hence removed
    return pubkey[1:]
