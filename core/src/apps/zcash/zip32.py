"""Implementation of ZIP-32 for Orchard
according to the https://zips.z.cash/zip-0032"""

from apps.common.seed import get_seed
from apps.common.keychain import Keychain

from trezor.crypto.hashlib import blake2b
from .address import SLIP44_ZCASH_COIN_TYPES
from apps.common.paths import PathSchema
from apps.common.keychain import FORBIDDEN_KEY_PATH
from trezor import log

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

    def spending_key(self):
        """Returns the Spending Key."""
        return self.sk

    def clone(self):
        return ExtendedSpendingKey(self.sk, self.c)

# deprecated
async def get_master(ctx):
    """Returns the Orchard master ExtendedSpendingKey."""
    log.warning(__name__, "Using deprecated method.")
    secret = await get_seed(ctx)
    return get_master_2(secret)

def get_master_2(seed):
    """Returns the Orchard master ExtendedSpendingKey."""
    I = blake2b(
        personal=b'ZcashIP32Orchard',
        data=seed
    ).digest()
    return ExtendedSpendingKey(sk=I[:32], c=I[32:])

# deprecated
def get_dummy_master():
    log.warning(__name__, "Using deprecated method.")
    return get_master_2(b"")

# deprecated
def verify_path(path):
    log.warning(__name__, "Using deprecated method.")
    schema = PathSchema.parse(PATTERN_ZIP32, SLIP44_ZCASH_COIN_TYPES)
    if not schema.match(path):
        raise FORBIDDEN_KEY_PATH

class Zip32Keychain(Keychain):
    def __init__(self, seed: bytes) -> None:
        schema = PathSchema.parse(PATTERN_ZIP32, SLIP44_ZCASH_COIN_TYPES)
        super().__init__(seed, "pallas", [schema])

    def root_fingerprint(self) -> int:
        raise NotImplementedError  # TODO

    def derive(self, path: paths.Bip32Path) -> bip32.HDNode:
        self.verify_path(path)
        return self._derive_with_cache(
            prefix_len=3,
            path=path,
            new_root=lambda: get_master_2(self.seed),
        )

    def derive_slip21(self, path: paths.Slip21Path) -> Slip21Node:
        raise NotImplementedError  # TODO


async def get_zip32_keychain(ctx):
    seed = await get_seed(ctx)
    return Zip32Keychain(seed)
