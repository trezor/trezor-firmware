from typing import TYPE_CHECKING

import storage.device as storage_device
from storage.cache_common import APP_COMMON_SEED_WITHOUT_PASSPHRASE
from trezor import utils
from trezor.crypto import hmac
from trezor.wire.context import get_context
from trezor.wire.errors import DataError

from apps.common import cache

from . import mnemonic
from .passphrase import get_passphrase

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from trezorcrypto import secbytes

    from trezor.crypto import bip32
    from trezor.messages import ThpCreateNewSession
    from trezor.wire.protocol_common import Context

    from .paths import Bip32Path, Slip21Path

if not utils.BITCOIN_ONLY:
    from storage.cache_common import APP_COMMON_DERIVE_CARDANO

if not utils.USE_THP:
    from .passphrase import get as get_passphrase_legacy


def raise_if_not_initialized() -> None:
    if not storage_device.is_initialized():
        from trezor.wire import NotInitialized

        raise NotInitialized("Device is not initialized")


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


class VaultSlip21Node:
    """
    SLIP-0021 node of a vault seed. The node and its keys stay sealed in the
    vault; use slip21_mac() for authentication tags.
    """

    def __init__(
        self, seed: secbytes | None = None, node: secbytes | None = None
    ) -> None:
        from trezorcrypto import slip21_derive

        if node is not None:
            self.node = node
        elif seed is not None:
            self.node = slip21_derive(seed, (), root=True)
        else:
            raise ValueError  # neither seed nor node specified

    def __del__(self) -> None:
        # Clones share the immutable record; owner teardown revokes it.
        del self.node

    def derive_path(self, path: Slip21Path) -> None:
        from trezorcrypto import slip21_derive

        if path:
            self.node = slip21_derive(self.node, path)

    def key(self) -> secbytes:
        from trezorcrypto import slip21_derive

        return slip21_derive(self.node, (), key=True)

    def clone(self) -> "VaultSlip21Node":
        return VaultSlip21Node(node=self.node)


def slip21_root(seed: bytes | secbytes) -> Slip21Node | VaultSlip21Node:
    if isinstance(seed, bytes):
        return Slip21Node(seed)
    return VaultSlip21Node(seed)


def slip21_export(seed: bytes | secbytes, path: Slip21Path) -> bytes:
    """Return a node the host receives by design (Evolu only)."""
    if isinstance(seed, bytes):
        node = Slip21Node(seed)
        node.derive_path(path)
        return node.data
    from trezorcrypto import slip21_export

    return slip21_export(seed, path)


def slip21_mac(key: bytes | secbytes, message: AnyBytes) -> bytes:
    """HMAC-SHA256 under a SLIP-0021 key; vault keys never leave the vault."""
    if isinstance(key, bytes):
        return hmac(hmac.SHA256, key, message).digest()
    return hmac.tag(hmac.SHA256, key, message)


def _store_common_seed(ctx: Context, passphrase: str) -> None:
    from trezorcrypto import retain_secret

    from trezor.crypto import bip32

    seed = bip32.from_storage(passphrase)
    retain_secret(seed)
    ctx.cache.vault_seed.take(seed)


def _check_cardano_supported(requested: bool) -> None:
    if requested:
        from trezor.wire.errors import ProcessError

        # Never reintroduce Python mnemonic access to service an unsupported
        # derivation. Native Cardano roots are a separate migration.
        raise ProcessError("Protected Cardano derivation is not implemented")


if utils.USE_THP:

    async def get_seed() -> secbytes:
        common_seed = get_context().cache.vault_seed
        assert not common_seed.empty()
        return common_seed

    async def derive_and_store_roots(ctx: Context, msg: ThpCreateNewSession) -> None:
        if msg.passphrase is not None and msg.on_device:
            raise DataError("Passphrase provided when it shouldn't be!")
        raise_if_not_initialized()
        if not ctx.cache.vault_seed.empty():
            raise Exception("Seed is already set!")
        if not utils.BITCOIN_ONLY:
            _check_cardano_supported(msg.derive_cardano)
        passphrase = await get_passphrase(msg)
        _store_common_seed(ctx, passphrase)

else:  # v1 protocol

    async def get_seed() -> secbytes:
        ctx = get_context()
        raise_if_not_initialized()
        if ctx.cache.vault_seed.empty():
            await derive_and_store_roots_legacy()
        return ctx.cache.vault_seed

    async def derive_and_store_roots_legacy() -> None:
        raise_if_not_initialized()
        ctx = get_context()
        if not utils.BITCOIN_ONLY:
            _check_cardano_supported(ctx.cache.get_bool(APP_COMMON_DERIVE_CARDANO))
        if not ctx.cache.vault_seed.empty():
            return
        passphrase = await get_passphrase_legacy()
        _store_common_seed(ctx, passphrase)


@cache.stored(APP_COMMON_SEED_WITHOUT_PASSPHRASE)
def _get_seed_without_passphrase() -> bytes:
    if not storage_device.is_initialized():
        raise Exception("Device is not initialized")
    return mnemonic.get_seed(progress_bar=False)


def derive_node_without_passphrase(
    path: Bip32Path, curve_name: str = "secp256k1"
) -> bip32.HDNode:
    from trezor.crypto import bip32

    seed = bip32.from_storage()
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
