from micropython import const

from apps.common import HARDENED
from apps.common.paths import PathSchema

SLIP44_ID = 1815

BYRON_ROOT = [44 | HARDENED, SLIP44_ID | HARDENED]
SHELLEY_ROOT = [1852 | HARDENED, SLIP44_ID | HARDENED]

# fmt: off
SCHEMA_PUBKEY = PathSchema("m/[44,1852]'/coin_type'/account'/*", SLIP44_ID)
SCHEMA_ADDRESS = PathSchema("m/[44,1852]'/coin_type'/account'/[0,1,2]/address_index", SLIP44_ID)
# staking is only allowed on Shelley paths with suffix /2/0
SCHEMA_STAKING = PathSchema("m/1852'/coin_type'/account'/2/0", SLIP44_ID)
# fmt: on

# the maximum allowed change address.  this should be large enough for normal
# use and still allow to quickly brute-force the correct bip32 path
MAX_CHANGE_ADDRESS_INDEX = const(1_000_000)
ACCOUNT_PATH_INDEX = const(2)
BIP_PATH_LENGTH = const(5)


def unharden(item: int) -> int:
    return item ^ (item & HARDENED)
