from typing import TYPE_CHECKING

from trezor.crypto import bech32

if TYPE_CHECKING:
    from buffer_types import AnyBytes

HRP_SEPARATOR = "1"

# CIP-0005 prefixes - https://github.com/cardano-foundation/CIPs/blob/master/CIP-0005/CIP-0005.md
HRP_ADDRESS = "addr"
HRP_TESTNET_ADDRESS = "addr_test"
HRP_REWARD_ADDRESS = "stake"
HRP_TESTNET_REWARD_ADDRESS = "stake_test"
HRP_CVOTE_PUBLIC_KEY = "cvote_vk"
HRP_SCRIPT_HASH = "script"
HRP_KEY_HASH = "addr_vkh"
HRP_SHARED_KEY_HASH = "addr_shared_vkh"
HRP_STAKE_KEY_HASH = "stake_vkh"
HRP_REQUIRED_SIGNER_KEY_HASH = "req_signer_vkh"
HRP_OUTPUT_DATUM_HASH = "datum"
HRP_SCRIPT_DATA_HASH = "script_data"
# CIP-0129 governance identifiers - https://github.com/cardano-foundation/CIPs/tree/master/CIP-0129
# both DRep key hash and script hash identifiers use the "drep" prefix
HRP_DREP = "drep"
# header byte: key type DRep (0b0010) in bits [7;4], credential type in bits [3;0]
DREP_HEADER_KEY_HASH = b"\x22"
DREP_HEADER_SCRIPT_HASH = b"\x23"


def encode(hrp: str, data: AnyBytes) -> str:
    converted_bits = bech32.convertbits(data, 8, 5)
    return bech32.bech32_encode(hrp, converted_bits, bech32.Encoding.BECH32)


def encode_drep(credential_hash: AnyBytes, is_script: bool) -> str:
    header = DREP_HEADER_SCRIPT_HASH if is_script else DREP_HEADER_KEY_HASH
    return encode(HRP_DREP, header + bytes(credential_hash))


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
