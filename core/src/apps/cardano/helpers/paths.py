from micropython import const

from apps.common.paths import HARDENED, PathSchema

SLIP44_ID = 1815

BYRON_ROOT = [44 | HARDENED, SLIP44_ID | HARDENED]
SHELLEY_ROOT = [1852 | HARDENED, SLIP44_ID | HARDENED]

# fmt: off
SCHEMA_PUBKEY = PathSchema.parse("m/[44,1852]'/coin_type'/account'/*", SLIP44_ID)
SCHEMA_PAYMENT = PathSchema.parse("m/[44,1852]'/coin_type'/account'/[0,1]/address_index", SLIP44_ID)
# staking is only allowed on Shelley paths with suffix /2/0
SCHEMA_STAKING = PathSchema.parse("m/1852'/coin_type'/account'/2/0", SLIP44_ID)
SCHEMA_STAKING_ANY_ACCOUNT = PathSchema.parse("m/1852'/coin_type'/[0-%s]'/2/0" % (HARDENED - 1), SLIP44_ID)
# fmt: on

ACCOUNT_PATH_LENGTH = const(3)
ACCOUNT_PATH_INDEX = const(2)

CHANGE_OUTPUT_PATH_NAME = "Change output path"
CHANGE_OUTPUT_STAKING_PATH_NAME = "Change output staking path"
CERTIFICATE_PATH_NAME = "Certificate path"
POOL_OWNER_STAKING_PATH_NAME = "Pool owner staking path"
WITNESS_PATH_NAME = "Witness path"


def unharden(item: int) -> int:
    return item ^ (item & HARDENED)
