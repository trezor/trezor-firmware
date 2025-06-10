from typing import TYPE_CHECKING

import storage.device as storage_device
from storage.cache_common import APP_COMMON_SEED, APP_COMMON_SEED_WITHOUT_PASSPHRASE
from trezor import utils
from trezor.crypto import hmac
from trezor.wire import context
from trezor.wire.context import get_context
from trezor.wire.errors import DataError

from apps.common import cache

from . import mnemonic
from .passphrase import get_passphrase as get_passphrase

if TYPE_CHECKING:
    from trezor.crypto import bip32
    from trezor.messages import ThpCreateNewSession
    from trezor.wire.protocol_common import Context

    from .paths import Bip32Path, Slip21Path

if not utils.BITCOIN_ONLY:
    from storage.cache_common import (
        APP_CARDANO_ICARUS_SECRET,
        APP_COMMON_DERIVE_CARDANO,
    )

if not utils.USE_THP:
    from .passphrase import get as get_passphrase_legacy


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


if utils.USE_THP:

    async def get_seed() -> bytes:  # type: ignore [Function declaration "get_seed" is obscured by a declaration of the same name]
        common_seed = context.cache_get(APP_COMMON_SEED)
        assert common_seed is not None
        return common_seed

    if utils.BITCOIN_ONLY:
        # === Bitcoin_only variant ===
        # We want to derive the normal seed ONLY

        async def derive_and_store_roots(
            ctx: Context, msg: ThpCreateNewSession
        ) -> None:

            if msg.passphrase is not None and msg.on_device:
                raise DataError("Passphrase provided when it shouldn't be!")

            if ctx.cache.is_set(APP_COMMON_SEED):
                raise Exception("Seed is already set!")

            from trezor import wire

            if not storage_device.is_initialized():
                raise wire.NotInitialized("Device is not initialized")

            passphrase = await get_passphrase(msg)
            common_seed = mnemonic.get_seed(passphrase)
            ctx.cache.set(APP_COMMON_SEED, common_seed)

    else:
        # === Cardano variant ===
        # We want to derive both the normal seed and the Cardano seed together
        async def derive_and_store_roots(
            ctx: Context, msg: ThpCreateNewSession
        ) -> None:

            if msg.passphrase is not None and msg.on_device:
                raise DataError("Passphrase provided when it shouldn't be!")

            from trezor import wire

            if not storage_device.is_initialized():
                raise wire.NotInitialized("Device is not initialized")

            if ctx.cache.is_set(APP_CARDANO_ICARUS_SECRET):
                raise Exception("Cardano icarus secret is already set!")

            passphrase = await get_passphrase(msg)
            common_seed = mnemonic.get_seed(passphrase)
            ctx.cache.set(APP_COMMON_SEED, common_seed)

            if msg.derive_cardano:
                from apps.cardano.seed import derive_and_store_secrets

                ctx.cache.set_bool(APP_COMMON_DERIVE_CARDANO, True)
                derive_and_store_secrets(ctx, passphrase)

else:
    if utils.BITCOIN_ONLY:
        # === Bitcoin-only variant ===
        # We use the simple version of `get_seed` that never needs to derive anything else.

        @cache.stored_async(APP_COMMON_SEED)
        async def get_seed() -> bytes:
            passphrase = await get_passphrase_legacy()
            return mnemonic.get_seed(passphrase=passphrase)

    else:
        # === Cardano variant ===
        # We want to derive both the normal seed and the Cardano seed together, AND
        # expose a method for Cardano to do the same

        @cache.stored_async(APP_COMMON_SEED)
        async def get_seed() -> bytes:
            await derive_and_store_roots_legacy()
            common_seed = context.cache_get(APP_COMMON_SEED)
            assert common_seed is not None
            return common_seed

        async def derive_and_store_roots_legacy() -> None:
            from trezor import wire

            if not storage_device.is_initialized():
                raise wire.NotInitialized("Device is not initialized")

            ctx = get_context()
            need_seed = not ctx.cache.is_set(APP_COMMON_SEED)
            need_cardano_secret = ctx.cache.get_bool(
                APP_COMMON_DERIVE_CARDANO
            ) and not ctx.cache.is_set(APP_CARDANO_ICARUS_SECRET)

            if not need_seed and not need_cardano_secret:
                return

            passphrase = await get_passphrase_legacy()

            if need_seed:
                common_seed = mnemonic.get_seed(passphrase)
                ctx.cache.set(APP_COMMON_SEED, common_seed)

            if need_cardano_secret:
                from apps.cardano.seed import derive_and_store_secrets

                derive_and_store_secrets(ctx, passphrase)


@cache.stored(APP_COMMON_SEED_WITHOUT_PASSPHRASE)
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
