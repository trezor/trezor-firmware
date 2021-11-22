"""Implementation of ZIP-32 for Orchard
according to the https://zips.z.cash/zip-0032"""

from apps.common import seed

from trezor.crypto.hashlib import blake2b
from .address import SLIP44_ZCASH_COIN_TYPES
from apps.common.paths import PathSchema
from apps.common.keychain import FORBIDDEN_KEY_PATH

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
    """Orchard Extended Spending Key."""
    def __init__(self, sk, c):
        self.sk = sk # spending key
        self.c = c   # chain code

    def child(self, i):
        """Derives the `i`-th child ExtendedSpendingKey."""
        assert i >= 1<<31
        I = prf_expand(self.c, bytes([0x81]) + self.sk + i2leosp_32(i))
        return ExtendedSpendingKey(sk=I[:32], c=I[32:])
    
    def derive(self, path):
        """Derives a descendant ExtendedSpendingKey according to the `path`."""
        state = self
        for digit in path:
            state = state.child(digit)
        return state

    def spending_key(self):
        """Returns the Spending Key."""
        return self.sk

async def get_master(ctx):
    """Returns the Orchard master ExtendedSpendingKey."""
    secret = await seed.get_seed(ctx)
    I = blake2b(
        personal=b'ZcashIP32Orchard',
        data=secret
    ).digest()
    return ExtendedSpendingKey(sk=I[:32], c=I[32:])

def verify_path(path):
    schema = PathSchema.parse(PATTERN_ZIP32, SLIP44_ZCASH_COIN_TYPES)
    if not schema.match(path):
        raise FORBIDDEN_KEY_PATH