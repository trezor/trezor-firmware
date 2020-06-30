from micropython import const

from trezor import wire
from trezor.crypto import bech32, bip32, der
from trezor.crypto.curve import secp256k1
from trezor.messages import InputScriptType, OutputScriptType
from trezor.utils import ensure

if False:
    from apps.common.coininfo import CoinInfo
    from typing import Dict
    from trezor.messages.TxInputType import EnumTypeInputScriptType
    from trezor.messages.TxOutputType import EnumTypeOutputScriptType


BITCOIN_NAMES = ("Bitcoin", "Regtest", "Testnet")

# Default signature hash type in Bitcoin which signs all inputs and all outputs of the transaction.
SIGHASH_ALL = const(0x01)

# The number of bip32 levels used in a wallet (chain and address)
BIP32_WALLET_DEPTH = const(2)

# supported witness version for bech32 addresses
_BECH32_WITVER = const(0x00)

MULTISIG_INPUT_SCRIPT_TYPES = (
    InputScriptType.SPENDMULTISIG,
    InputScriptType.SPENDP2SHWITNESS,
    InputScriptType.SPENDWITNESS,
)
MULTISIG_OUTPUT_SCRIPT_TYPES = (
    OutputScriptType.PAYTOMULTISIG,
    OutputScriptType.PAYTOP2SHWITNESS,
    OutputScriptType.PAYTOWITNESS,
)

CHANGE_OUTPUT_TO_INPUT_SCRIPT_TYPES = {
    OutputScriptType.PAYTOADDRESS: InputScriptType.SPENDADDRESS,
    OutputScriptType.PAYTOMULTISIG: InputScriptType.SPENDMULTISIG,
    OutputScriptType.PAYTOP2SHWITNESS: InputScriptType.SPENDP2SHWITNESS,
    OutputScriptType.PAYTOWITNESS: InputScriptType.SPENDWITNESS,
}  # type: Dict[EnumTypeOutputScriptType, EnumTypeInputScriptType]
INTERNAL_INPUT_SCRIPT_TYPES = tuple(CHANGE_OUTPUT_TO_INPUT_SCRIPT_TYPES.values())
CHANGE_OUTPUT_SCRIPT_TYPES = tuple(CHANGE_OUTPUT_TO_INPUT_SCRIPT_TYPES.keys())

SEGWIT_INPUT_SCRIPT_TYPES = (
    InputScriptType.SPENDP2SHWITNESS,
    InputScriptType.SPENDWITNESS,
)

NONSEGWIT_INPUT_SCRIPT_TYPES = (
    InputScriptType.SPENDADDRESS,
    InputScriptType.SPENDMULTISIG,
)


def ecdsa_sign(node: bip32.HDNode, digest: bytes) -> bytes:
    sig = secp256k1.sign(node.private_key(), digest)
    sigder = der.encode_seq((sig[1:33], sig[33:65]))
    return sigder


def ecdsa_hash_pubkey(pubkey: bytes, coin: CoinInfo) -> bytes:
    if pubkey[0] == 0x04:
        ensure(len(pubkey) == 65)  # uncompressed format
    elif pubkey[0] == 0x00:
        ensure(len(pubkey) == 1)  # point at infinity
    else:
        ensure(len(pubkey) == 33)  # compresssed format

    return coin.script_hash(pubkey)


def encode_bech32_address(prefix: str, script: bytes) -> str:
    address = bech32.encode(prefix, _BECH32_WITVER, script)
    if address is None:
        raise wire.ProcessError("Invalid address")
    return address


def decode_bech32_address(prefix: str, address: str) -> bytes:
    witver, raw = bech32.decode(prefix, address)
    if witver != _BECH32_WITVER:
        raise wire.ProcessError("Invalid address witness program")
    return bytes(raw)
