from trezor.crypto import bech32

HRP_SEPARATOR = "1"

# CIP-0005 prefixes - https://github.com/cardano-foundation/CIPs/blob/master/CIP-0005/CIP-0005.md
HRP_ADDRESS = "addr"
HRP_TESTNET_ADDRESS = "addr_test"
HRP_REWARD_ADDRESS = "stake"
HRP_TESTNET_REWARD_ADDRESS = "stake_test"
HRP_GOVERNANCE_PUBLIC_KEY = "gov_vk"
HRP_SCRIPT_HASH = "script"
HRP_KEY_HASH = "addr_vkh"
HRP_SHARED_KEY_HASH = "addr_shared_vkh"
HRP_STAKE_KEY_HASH = "stake_vkh"
HRP_REQUIRED_SIGNER_KEY_HASH = "req_signer_vkh"
HRP_OUTPUT_DATUM_HASH = "datum"
HRP_SCRIPT_DATA_HASH = "script_data"


def encode(hrp: str, data: bytes) -> str:
    converted_bits = bech32.convertbits(data, 8, 5)
    return bech32.bech32_encode(hrp, converted_bits, bech32.Encoding.BECH32)


def decode_unsafe(bech: str) -> bytes:
    hrp = bech.rsplit(HRP_SEPARATOR, 1)[0]
    return _decode(hrp, bech)


def _decode(hrp: str, bech: str) -> bytes:
    decoded_hrp, data, spec = bech32.bech32_decode(bech, 130)
    if decoded_hrp != hrp:
        raise ValueError
    if spec != bech32.Encoding.BECH32:
        raise ValueError

    decoded = bech32.convertbits(data, 5, 8, False)
    return bytes(decoded)
