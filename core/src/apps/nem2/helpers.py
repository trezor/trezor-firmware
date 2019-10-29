from micropython import const

from apps.common import HARDENED

NEM_NETWORK_MAINNET = const(0x68)
NEM_NETWORK_TESTNET = const(0x98)
NEM_NETWORK_MIJIN = const(0x60)
NEM_NETWORK_MIJIN_TEST = const(0x90)

NEM_TRANSACTION_TYPE_TRANSFER = const(0x4154)

NEM_MAX_DIVISIBILITY = const(6)
NEM_MAX_SUPPLY = const(9000000000000000)

NEM_SALT_SIZE = const(32)
AES_BLOCK_SIZE = const(16)
NEM_HASH_ALG = "keccak"
NEM_PUBLIC_KEY_SIZE = const(32)  # ed25519 public key

NEM_MAX_PLAIN_PAYLOAD_SIZE = const(1024)
NEM_MAX_ENCRYPTED_PAYLOAD_SIZE = const(960)


def check_path(path: list, network=None) -> bool:
    """
    Validates derivation path to fit 44'/43'/a'
    """
    length = len(path)
    if length != 3:
        return False
    if path[0] != 44 | HARDENED:
        return False
    if path[1] != 43 | HARDENED:
        return False
    if path[2] < HARDENED or path[2] > 1000000 | HARDENED:
        return False
    return True
