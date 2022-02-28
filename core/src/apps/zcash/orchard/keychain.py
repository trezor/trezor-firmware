"""Implementation of ZIP-32 for Orchard
according to the https://zips.z.cash/zip-0032"""

from apps.common.seed import get_seed
from apps.common.keychain import Keychain
from trezor.messages import SignTx

from trezor.crypto.hashlib import blake2b
from ..address import SLIP44_ZCASH_COIN_TYPES
from apps.common.paths import PathSchema
from apps.common.keychain import FORBIDDEN_KEY_PATH
from trezor import log
from trezor.crypto import orchardlib
from apps.bitcoin.keychain import get_coin_by_name

# Tested against the zcash/orchard crate.
# TODO: Add official unittests (waiting for ZIP-32 testvectors).

PATTERN_ZIP32 = "m/32'/coin_type'/account'"


def i2leosp_32(x):
    """Converts uint32 to 4 bytes in little endian."""
    assert 0 <= x <= 0xFFFF_FFFF
    return bytes([(x >> i) & 0xFF for i in [0, 8, 16, 24]])


def prf_expand(sk, t):
    """Zcash PRF^{expand} function."""
    digest = blake2b(personal=b'Zcash_ExpandSeed')
    digest.update(sk)
    digest.update(t)
    return digest.digest()


class ExtendedSpendingKey:
    """Orchard Extended Spending Key.
    Equivalent for bip32.HDNode."""
    def __init__(self, sk, c):
        self.sk = sk  # spending key
        self.c = c    # chain code

    def child(self, i):
        """Derives the `i`-th child ExtendedSpendingKey."""
        assert i >= 1<<31
        I = prf_expand(self.c, bytes([0x81]) + self.sk + i2leosp_32(i))
        return ExtendedSpendingKey(sk=I[:32], c=I[32:])

    # deprecated
    def derive(self, path):
        """Derives a descendant ExtendedSpendingKey according to the `path`."""
        log.warning(__name__, "Using deprecated method.")
        return self.derive_path(path)

    def derive_path(self, path):
        """Derives a descendant ExtendedSpendingKey according to the `path`."""
        state = self
        for digit in path:
            state = state.child(digit)
        return state

    def clone(self):
        return ExtendedSpendingKey(self.sk, self.c)

    def spending_key(self):
        """Returns the Spending Key."""
        return self.sk

    def full_viewing_key(self):
        """Returns the Full Vieving Key."""
        fvk_bytes = orchardlib.derive_full_viewing_key(self.sk, False)  # TODO: remove internal
        return FullViewingKey(fvk_bytes)

    @staticmethod
    def get_master(seed):
        """Returns the Orchard master ExtendedSpendingKey."""
        I = blake2b(
            personal=b'ZcashIP32Orchard',
            data=seed
        ).digest()
        return ExtendedSpendingKey(sk=I[:32], c=I[32:])


class FullViewingKey:
    """Orchard Full Vieving Key."""
    def __init__(self, fvk):
        self.fvk = fvk

    def raw(self, internal=False):
        if internal:
            return orchardlib.derive_internal_full_viewing_key(self.fvk)
        else:
            return self.fvk

    def incoming_viewing_key(self, internal=False):
        """Returns the Incoming Vieving Key."""
        return orchardlib.derive_incoming_viewing_key(self.fvk, internal)

    def outgoing_viewing_key(self, internal=False):
        """Returns the Outgoing Vieving Key."""
        return orchardlib.derive_outgoing_viewing_key(self.fvk, internal)

    def address(self, diversifier=0, internal=False):
        return orchardlib.derive_address(self.fvk, diversifier, internal)


class OrchardKeychain(Keychain):
    def __init__(self, seed: bytes, coin) -> None:
        assert coin.slip44 in SLIP44_ZCASH_COIN_TYPES
        schema = PathSchema.parse(PATTERN_ZIP32, (coin.slip44,))
        super().__init__(seed, "pallas", [schema])

    def root_fingerprint(self) -> int:
        raise NotImplementedError  # TODO ?

    def derive(self, path: paths.Bip32Path) -> bip32.HDNode:
        self.verify_path(path)
        return self._derive_with_cache(
            prefix_len=3,
            path=path,
            new_root=lambda: ExtendedSpendingKey.get_master(self.seed),
        )

    def derive_slip21(self, path: paths.Slip21Path) -> Slip21Node:
        raise NotImplementedError  # TODO ?


async def get_keychain_for_coin(ctx, coin):
    seed = await get_seed(ctx)
    return OrchardKeychain(seed, coin)


def with_keychain(func):
    async def wrapper(ctx, msg):
        coin = get_coin_by_name(msg.coin_name)
        keychain = await get_keychain_for_coin(ctx, coin)
        return await func(ctx, msg, keychain)

    return wrapper

