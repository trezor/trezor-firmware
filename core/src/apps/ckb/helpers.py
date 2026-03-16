"""CKB helper functions for address generation."""

from ubinascii import unhexlify

from trezor.crypto.hashlib import blake2b
from trezor.crypto.bech32 import bech32_encode, Encoding, convertbits

# System script code_hash for secp256k1_blake160_sighash_all
# Same on both Mainnet (Lina) and Testnet (Aggron)
CODE_HASH_SECP256K1_BLAKE160 = unhexlify(
    "9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8"
)

# Hash type: Type (0x01)
HASH_TYPE = 0x01

# Human-readable parts for Bech32m encoding
HRP_MAINNET = "ckb"
HRP_TESTNET = "ckt"


def pubkey_to_blake160(public_key: bytes) -> bytes:
    """Hash public key with Blake2b and take first 20 bytes (blake160)."""
    h = blake2b(
        data=public_key,
        outlen=32,
        personal=b"ckb-default-hash",
    )
    return h.digest()[:20]


def script_to_address(args: bytes, network: str) -> str:
    """
    Encode lock script to Bech32m address using CKB2021 Full format.

    CKB2021 Full address format:
    - Payload: 0x00 (full format) | code_hash (32B) | hash_type (1B) | args (20B)
    """
    # Full format payload for SECP256K1_BLAKE160:
    # 0x00 = full format flag
    # code_hash = 32 bytes (secp256k1_blake160_sighash_all)
    # hash_type = 0x01 (Type)
    # args = 20 bytes (blake160 of pubkey)
    payload_bytes = (
        bytes([0x00]) + CODE_HASH_SECP256K1_BLAKE160 + bytes([HASH_TYPE]) + args
    )

    # Convert from 8-bit to 5-bit for bech32
    payload_5bit = convertbits(payload_bytes, 8, 5)

    # Select HRP based on network
    hrp = HRP_MAINNET if network == "Mainnet" else HRP_TESTNET

    # Encode with Bech32m (not Bech32)
    address = bech32_encode(hrp, payload_5bit, Encoding.BECH32M)

    return address
