from micropython import const
from typing import TYPE_CHECKING

from trezor import wire
from trezor.crypto import bech32
from trezor.crypto.curve import bip340
from trezor.enums import InputScriptType, OutputScriptType

if TYPE_CHECKING:
    from enum import IntEnum

    from trezor.crypto import bip32
    from trezor.messages import TxInput
    from trezor.utils import HashWriter

    from apps.common.coininfo import CoinInfo
else:
    IntEnum = object


BITCOIN_NAMES = ("Bitcoin", "Regtest", "Testnet")


class SigHashType(IntEnum):
    """Enumeration type listing the supported signature hash types.

    Class constants defined below don't need to be used in the code.
    They are a list of all allowed incoming sighash types.
    """

    # Signature hash type with the same semantics as SIGHASH_ALL, but instead
    # of having to include the byte in the signature, it is implied.
    SIGHASH_ALL_TAPROOT = 0x00

    # Default signature hash type in Bitcoin which signs all inputs and all
    # outputs of the transaction.
    SIGHASH_ALL = 0x01

    # Signature hash flag used in some Bitcoin-like altcoins for replay
    # protection.
    SIGHASH_FORKID = 0x40

    # Signature hash type with the same semantics as SIGHASH_ALL. Used in some
    # Bitcoin-like altcoins for replay protection.
    SIGHASH_ALL_FORKID = 0x41

    @classmethod
    def from_int(cls, sighash_type: int) -> "SigHashType":
        for val in cls.__dict__.values():  # type: SigHashType
            if val == sighash_type:
                return val
        raise ValueError("Unsupported sighash type.")


# The number of bip32 levels used in a wallet (chain and address)
BIP32_WALLET_DEPTH = const(2)

# Bitcoin opcodes
OP_0 = const(0x00)
OP_1 = const(0x51)

# supported witness versions for bech32 addresses
_BECH32_WITVERS = (0, 1)

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

CHANGE_OUTPUT_TO_INPUT_SCRIPT_TYPES: dict[OutputScriptType, InputScriptType] = {
    OutputScriptType.PAYTOADDRESS: InputScriptType.SPENDADDRESS,
    OutputScriptType.PAYTOMULTISIG: InputScriptType.SPENDMULTISIG,
    OutputScriptType.PAYTOP2SHWITNESS: InputScriptType.SPENDP2SHWITNESS,
    OutputScriptType.PAYTOWITNESS: InputScriptType.SPENDWITNESS,
    OutputScriptType.PAYTOTAPROOT: InputScriptType.SPENDTAPROOT,
}

INTERNAL_INPUT_SCRIPT_TYPES = tuple(CHANGE_OUTPUT_TO_INPUT_SCRIPT_TYPES.values())
CHANGE_OUTPUT_SCRIPT_TYPES = tuple(CHANGE_OUTPUT_TO_INPUT_SCRIPT_TYPES.keys())

SEGWIT_INPUT_SCRIPT_TYPES = (
    InputScriptType.SPENDP2SHWITNESS,
    InputScriptType.SPENDWITNESS,
    InputScriptType.SPENDTAPROOT,
)

SEGWIT_OUTPUT_SCRIPT_TYPES = (
    OutputScriptType.PAYTOP2SHWITNESS,
    OutputScriptType.PAYTOWITNESS,
    OutputScriptType.PAYTOTAPROOT,
)

NONSEGWIT_INPUT_SCRIPT_TYPES = (
    InputScriptType.SPENDADDRESS,
    InputScriptType.SPENDMULTISIG,
)


def ecdsa_sign(node: bip32.HDNode, digest: bytes) -> bytes:
    from trezor.crypto import der
    from trezor.crypto.curve import secp256k1

    sig = secp256k1.sign(node.private_key(), digest)
    sigder = der.encode_seq((sig[1:33], sig[33:65]))
    return sigder


def bip340_sign(node: bip32.HDNode, digest: bytes) -> bytes:
    internal_private_key = node.private_key()
    output_private_key = bip340.tweak_secret_key(internal_private_key)
    return bip340.sign(output_private_key, digest)


def ecdsa_hash_pubkey(pubkey: bytes, coin: CoinInfo) -> bytes:
    from trezor.utils import ensure

    if pubkey[0] == 0x04:
        ensure(len(pubkey) == 65)  # uncompressed format
    elif pubkey[0] == 0x00:
        ensure(len(pubkey) == 1)  # point at infinity
    else:
        ensure(len(pubkey) == 33)  # compresssed format

    return coin.script_hash(pubkey).digest()


def encode_bech32_address(prefix: str, witver: int, script: bytes) -> str:
    assert witver in _BECH32_WITVERS
    address = bech32.encode(prefix, witver, script)
    if address is None:
        raise wire.ProcessError("Invalid address")
    return address


def decode_bech32_address(prefix: str, address: str) -> tuple[int, bytes]:
    witver, raw = bech32.decode(prefix, address)
    if witver not in _BECH32_WITVERS:
        raise wire.DataError("Invalid address witness program")
    assert witver is not None
    assert raw is not None
    # check that P2TR address encodes a valid BIP340 public key
    if witver == 1 and not bip340.verify_publickey(raw):
        raise wire.DataError("Invalid Taproot witness program")
    return witver, raw


def input_is_segwit(txi: TxInput) -> bool:
    # Note that we don't investigate whether external inputs that are not presigned
    # are SegWit or not. For practical purposes we count them as SegWit, because
    # they behave as such, i.e. they don't use get_legacy_tx_digest().
    return txi.script_type in SEGWIT_INPUT_SCRIPT_TYPES or (
        txi.script_type == InputScriptType.EXTERNAL
        and bool(txi.witness or not txi.script_sig)
    )


def input_is_taproot(txi: TxInput) -> bool:
    if txi.script_type == InputScriptType.SPENDTAPROOT:
        return True

    if txi.script_type == InputScriptType.EXTERNAL:
        assert txi.script_pubkey is not None
        if txi.script_pubkey[0] == OP_1:
            return True

    return False


def input_is_external(txi: TxInput) -> bool:
    return txi.script_type == InputScriptType.EXTERNAL


def input_is_external_unverified(txi: TxInput) -> bool:
    return (
        txi.script_type == InputScriptType.EXTERNAL
        and txi.ownership_proof is None
        and txi.witness is None
        and txi.script_sig is None
    )


def tagged_hashwriter(tag: bytes) -> HashWriter:
    from trezor.crypto.hashlib import sha256
    from trezor.utils import HashWriter

    tag_digest = sha256(tag).digest()
    ctx = sha256(tag_digest)
    ctx.update(tag_digest)
    return HashWriter(ctx)


def format_fee_rate(
    fee_rate: float, coin: CoinInfo, include_shortcut: bool = False
) -> str:
    from trezor.strings import format_amount

    # Use format_amount to get correct thousands separator -- micropython's built-in
    # formatting doesn't add thousands sep to floating point numbers.
    # We multiply by 100 to get a fixed-point integer with two decimal places,
    # and add 0.5 to round to the nearest integer.
    fee_rate_formatted = format_amount(int(fee_rate * 100 + 0.5), 2)

    if include_shortcut and coin.coin_shortcut != "BTC":
        shortcut = " " + coin.coin_shortcut
    else:
        shortcut = ""

    return f"{fee_rate_formatted} sat{shortcut}/{'v' if coin.segwit else ''}B"
