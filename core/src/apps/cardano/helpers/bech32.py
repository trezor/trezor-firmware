from trezor.crypto import bech32

HRP_SEPARATOR = "1"

# CIP-0005 prefixes - https://github.com/cardano-foundation/CIPs/blob/master/CIP-0005/CIP-0005.md
HRP_ADDRESS = "addr"
HRP_TESTNET_ADDRESS = "addr_test"
HRP_REWARD_ADDRESS = "stake"
HRP_TESTNET_REWARD_ADDRESS = "stake_test"
# Jormungandr public key prefix - https://github.com/input-output-hk/voting-tools-lib/blob/18dae637e80db72444476606ab264b973bcf1a9d/src/Cardano/API/Extended.hs#L226
HRP_JORMUN_PUBLIC_KEY = "ed25519_pk"
HRP_SCRIPT_HASH = "script"
HRP_KEY_HASH = "addr_vkh"
HRP_SHARED_KEY_HASH = "addr_shared_vkh"


def encode(hrp: str, data: bytes) -> str:
    converted_bits = bech32.convertbits(data, 8, 5)
    return bech32.bech32_encode(hrp, converted_bits, bech32.Encoding.BECH32)


def decode_unsafe(bech: str) -> bytes:
    hrp = get_hrp(bech)
    return decode(hrp, bech)


def get_hrp(bech: str) -> str:
    return bech.rsplit(HRP_SEPARATOR, 1)[0]


def decode(hrp: str, bech: str) -> bytes:
    decoded_hrp, data, spec = bech32.bech32_decode(bech, 130)
    if data is None:
        raise ValueError
    if decoded_hrp != hrp:
        raise ValueError
    if spec != bech32.Encoding.BECH32:
        raise ValueError

    decoded = bytes(bech32.convertbits(data, 5, 8, False))
    return bytes(decoded)
