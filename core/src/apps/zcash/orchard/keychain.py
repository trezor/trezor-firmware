"""
Implementation of Orchard key derivation scheme
for deterministic wallets according to the ZIP-32.

see: https://zips.z.cash/zip-0032
"""

from typing import TYPE_CHECKING

from apps.common.seed import get_seed
from apps.common.keychain import Keychain
from trezor.messages import SignTx
from trezor.enums import ZcashKeychainScope as Scope

from trezor.crypto.hashlib import blake2b
from apps.common.paths import PathSchema
from apps.common.keychain import FORBIDDEN_KEY_PATH
from trezor.crypto import orchardlib
from apps.bitcoin.keychain import get_coin_by_name

if TYPE_CHECKING:
    from typing import Sequence
    from apps.common.coininfo import CoinInfo
    from apps.common.paths import Bip32Path, Slip21Path

PATTERN_ZIP32 = "m/32'/coin_type'/account'"

def i2leosp_32(x: int) -> bytes:
    """Converts uint32 to 4 bytes in little-endian order."""
    assert 0 <= x <= 0xFFFF_FFFF
    return bytes([
        (x >> 0) & 0xFF,
        (x >> 8) & 0xFF,
        (x >> 16) & 0xFF,
        (x >> 24) & 0xFF,
    ])


def prf_expand(sk: bytes, t: bytes) -> bytes:
    """Zcash PRF^{expand} function."""
    digest = blake2b(personal=b'Zcash_ExpandSeed')
    digest.update(sk)
    digest.update(t)
    return digest.digest()


class ExtendedSpendingKey:
    """Orchard Extended Spending Key."""
    def __init__(self, sk: bytes, c: bytes) -> None:
        self.sk = sk  # spending key
        self.c = c    # chain code

    def spending_key(self) -> bytes:
        """Returns the Spending Key."""
        return self.sk

    def full_viewing_key(self) -> FullViewingKey:
        """Returns the Full Vieving Key."""
        fvk_bytes = orchardlib.derive_full_viewing_key(self.sk)
        return FullViewingKey(fvk_bytes)

    @staticmethod
    def get_master(seed: bytes) -> ExtendedSpendingKey:
        """Generates the Orchard master ExtendedSpendingKey from `seed`."""
        I = blake2b(
            personal=b'ZcashIP32Orchard',
            data=seed
        ).digest()
        return ExtendedSpendingKey(sk=I[:32], c=I[32:])

    # apps.common.keychain.NodeProtocol methods:

    def derive_path(self, path: Bip32Path) -> None:
        """Derives a descendant ExtendedSpendingKey according to the `path`."""
        for i in path:
            assert i >= 1<<31
            I = prf_expand(self.c, bytes([0x81]) + self.sk + i2leosp_32(i))
            self.sk, self.c = I[:32], I[32:]

    def clone(self) -> ExtendedSpendingKey:
        return ExtendedSpendingKey(self.sk, self.c)


class FullViewingKey:
    """Orchard Full Vieving Key."""
    def __init__(self, fvk: bytes):
        self.fvk = fvk

    def raw(self) -> bytes:
        return self.fvk

    def incoming_viewing_key(self, scope: Scope = Scope.EXTERNAL) -> bytes:
        """Returns the Incoming Vieving Key."""
        return orchardlib.derive_incoming_viewing_key(self.fvk, scope)

    def outgoing_viewing_key(self, scope: Scope = Scope.EXTERNAL) -> bytes:
        """Returns the Outgoing Vieving Key."""
        return orchardlib.derive_outgoing_viewing_key(self.fvk, scope)

    def address(self, diversifier: int = 0, scope: Scope = Scope.EXTERNAL) -> bytes:
        return orchardlib.derive_address(self.fvk, diversifier, scope)


class OrchardKeychain(Keychain):
    def __init__(self, seed: bytes, coin: CoinInfo) -> None:
        schema = PathSchema.parse(PATTERN_ZIP32, (coin.slip44,))
        super().__init__(seed, "pallas", [schema])

    def derive(self, path: Bip32Path) -> ExtendedSpendingKey:
        self.verify_path(path)
        return self._derive_with_cache(
            prefix_len=3,
            path=path,
            new_root=lambda: ExtendedSpendingKey.get_master(self.seed),
        )

    def derive_slip21(self, path: Slip21Path) -> Slip21Node:
        raise NotImplementedError  # TODO ?

    def root_fingerprint(self) -> int:
        raise NotImplementedError  # TODO ?


async def get_keychain_for_coin(ctx: Context, coin: CoinInfo) -> OrchardKeychain:
    seed = await get_seed(ctx)
    return OrchardKeychain(seed, coin)


def with_keychain(func):
    async def wrapper(ctx, msg):
        coin = get_coin_by_name(msg.coin_name)
        keychain = await get_keychain_for_coin(ctx, coin)
        return await func(ctx, msg, keychain)

    return wrapper
