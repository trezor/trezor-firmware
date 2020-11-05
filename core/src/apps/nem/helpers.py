from micropython import const

from apps.common import HARDENED, paths

from . import SLIP44_ID

NEM_NETWORK_MAINNET = const(0x68)
NEM_NETWORK_TESTNET = const(0x98)
NEM_NETWORK_MIJIN = const(0x60)

NEM_TRANSACTION_TYPE_TRANSFER = const(0x0101)
NEM_TRANSACTION_TYPE_IMPORTANCE_TRANSFER = const(0x0801)
NEM_TRANSACTION_TYPE_AGGREGATE_MODIFICATION = const(0x1001)
NEM_TRANSACTION_TYPE_MULTISIG_SIGNATURE = const(0x1002)
NEM_TRANSACTION_TYPE_MULTISIG = const(0x1004)
NEM_TRANSACTION_TYPE_PROVISION_NAMESPACE = const(0x2001)
NEM_TRANSACTION_TYPE_MOSAIC_CREATION = const(0x4001)
NEM_TRANSACTION_TYPE_MOSAIC_SUPPLY_CHANGE = const(0x4002)

NEM_MAX_DIVISIBILITY = const(6)
NEM_MAX_SUPPLY = const(9000000000)

NEM_SALT_SIZE = const(32)
AES_BLOCK_SIZE = const(16)
NEM_HASH_ALG = "keccak"
NEM_PUBLIC_KEY_SIZE = const(32)  # ed25519 public key
NEM_LEVY_PERCENTILE_DIVISOR_ABSOLUTE = const(10000)
NEM_MOSAIC_AMOUNT_DIVISOR = const(1000000)

NEM_MAX_PLAIN_PAYLOAD_SIZE = const(1024)
NEM_MAX_ENCRYPTED_PAYLOAD_SIZE = const(960)


def get_network_str(network: int) -> str:
    if network == NEM_NETWORK_MAINNET:
        return "Mainnet"
    elif network == NEM_NETWORK_TESTNET:
        return "Testnet"
    elif network == NEM_NETWORK_MIJIN:
        return "Mijin"


def check_path(path: paths.Bip32Path, network: int) -> bool:
    """Validates that the appropriate coin_type is set for the given network."""
    if len(path) < 2:
        return False

    coin_type = path[1] - HARDENED

    if network == NEM_NETWORK_TESTNET:
        return coin_type == 1

    if network in (NEM_NETWORK_MAINNET, NEM_NETWORK_MIJIN):
        return coin_type == SLIP44_ID

    # unknown network
    return False
