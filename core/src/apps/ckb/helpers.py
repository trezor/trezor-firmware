"""CKB helper functions for address generation."""

from ubinascii import unhexlify

from trezor.crypto.hashlib import blake2b
from trezor.crypto.bech32 import bech32_encode, Encoding, convertbits

# System script code_hash for secp256k1_blake160_sighash_all
# Same on both Mainnet and Testnet
CODE_HASH_SECP256K1_BLAKE160 = unhexlify(
    "9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8"
)

# Hash type: Type (0x01)
HASH_TYPE = 0x01

# Human-readable parts for Bech32m encoding
HRP_MAINNET = "ckb"
HRP_TESTNET = "ckt"


def get_lock_script_arg(public_key: bytes) -> bytes:
    """Hash public key with Blake2b and return first 20 bytes (lock script argument)."""
    h = blake2b(
        data=public_key,
        outlen=32,
        personal=b"ckb-default-hash",
    )
    return h.digest()[:20]


def encode_address(args: bytes, network: str) -> str:
    """Encode default secp256k1_blake160 lock script to Bech32m address."""
    return encode_address_full(CODE_HASH_SECP256K1_BLAKE160, HASH_TYPE, args, network)


def encode_address_full(
    code_hash: bytes, hash_type: int, args: bytes, network: str
) -> str:
    """
    Encode any lock script to Bech32m address using CKB2021 Full format.
    Supports any lock script (secp256k1, omnilock, etc.)
    """
    payload_bytes = bytes([0x00]) + code_hash + bytes([hash_type]) + args

    payload_5bit = convertbits(payload_bytes, 8, 5)

    hrp = HRP_MAINNET if network == "Mainnet" else HRP_TESTNET

    return bech32_encode(hrp, payload_5bit, Encoding.BECH32M)


def format_amount(shannons: int) -> str:
    """
    Format capacity in shannons as human-readable CKB string.
    1 CKB = 10^8 shannons.
    Uses integer arithmetic to avoid float precision issues.
    """
    whole = shannons // 100_000_000
    frac = shannons % 100_000_000
    if frac == 0:
        return f"{whole} CKB"
    # Format fractional part with leading zeros, then strip trailing zeros
    frac_str = f"{frac:08d}".rstrip("0")
    return f"{whole}.{frac_str} CKB"
