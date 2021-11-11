from trezor import utils, wire
from trezor.crypto import base58
from trezor.crypto.base58 import blake256d_32
from trezor.enums import InputScriptType

from apps.common.writers import write_bytes_fixed, write_uint64_le

from . import scripts
from .common import SigHashType
from .multisig import multisig_get_pubkeys, multisig_pubkey_index
from .scripts import (  # noqa: F401
    output_script_paytoopreturn,
    write_output_script_multisig,
    write_output_script_p2pkh,
)
from .writers import op_push_length, write_bitcoin_varint, write_op_push

if False:
    from trezor.messages import MultisigRedeemScriptType

    from apps.common.coininfo import CoinInfo

    from .writers import Writer


def write_input_script_prefixed(
    w: Writer,
    script_type: InputScriptType,
    multisig: MultisigRedeemScriptType | None,
    coin: CoinInfo,
    sighash_type: SigHashType,
    pubkey: bytes,
    signature: bytes,
) -> None:
    if script_type == InputScriptType.SPENDADDRESS:
        # p2pkh or p2sh
        scripts.write_input_script_p2pkh_or_p2sh_prefixed(
            w, pubkey, signature, sighash_type
        )
    elif script_type == InputScriptType.SPENDMULTISIG:
        # p2sh multisig
        assert multisig is not None  # checked in sanitize_tx_input
        signature_index = multisig_pubkey_index(multisig, pubkey)
        write_input_script_multisig_prefixed(
            w, multisig, signature, signature_index, sighash_type, coin
        )
    else:
        raise wire.ProcessError("Invalid script type")


def write_input_script_multisig_prefixed(
    w: Writer,
    multisig: MultisigRedeemScriptType,
    signature: bytes,
    signature_index: int,
    sighash_type: SigHashType,
    coin: CoinInfo,
) -> None:
    signatures = multisig.signatures  # other signatures
    if len(signatures[signature_index]) > 0:
        raise wire.DataError("Invalid multisig parameters")
    signatures[signature_index] = signature  # our signature

    # length of the redeem script
    pubkeys = multisig_get_pubkeys(multisig)
    redeem_script_length = scripts.output_script_multisig_length(pubkeys, multisig.m)

    # length of the result
    total_length = 0
    for s in signatures:
        if s:
            total_length += 1 + len(s) + 1  # length, signature, hash_type
    total_length += op_push_length(redeem_script_length) + redeem_script_length
    write_bitcoin_varint(w, total_length)

    for s in signatures:
        if s:
            scripts.append_signature(w, s, sighash_type)

    # redeem script
    write_op_push(w, redeem_script_length)
    scripts.write_output_script_multisig(w, pubkeys, multisig.m)


# A ticket purchase submission for an address hash.
def output_script_sstxsubmissionpkh(addr: str) -> bytearray:
    try:
        raw_address = base58.decode_check(addr, blake256d_32)
    except ValueError:
        raise wire.DataError("Invalid address")

    w = utils.empty_bytearray(26)
    w.append(0xBA)  # OP_SSTX
    scripts.write_output_script_p2pkh(w, raw_address[2:])
    return w


# Ticket purchase change script.
def output_script_sstxchange(addr: str) -> bytearray:
    try:
        raw_address = base58.decode_check(addr, blake256d_32)
    except ValueError:
        raise wire.DataError("Invalid address")

    w = utils.empty_bytearray(26)
    w.append(0xBD)  # OP_SSTXCHANGE
    scripts.write_output_script_p2pkh(w, raw_address[2:])
    return w


# Spend from a stake revocation.
def write_output_script_ssrtx_prefixed(w: Writer, pkh: bytes) -> None:
    utils.ensure(len(pkh) == 20)
    write_bitcoin_varint(w, 26)
    w.append(0xBC)  # OP_SSRTX
    scripts.write_output_script_p2pkh(w, pkh)


# Spend from a stake generation.
def write_output_script_ssgen_prefixed(w: Writer, pkh: bytes) -> None:
    utils.ensure(len(pkh) == 20)
    write_bitcoin_varint(w, 26)
    w.append(0xBB)  # OP_SSGEN
    scripts.write_output_script_p2pkh(w, pkh)


# Stake commitment OPRETURN.
def sstxcommitment_pkh(pkh: bytes, amount: int) -> bytes:
    w = utils.empty_bytearray(30)
    write_bytes_fixed(w, pkh, 20)
    write_uint64_le(w, amount)
    write_bytes_fixed(w, b"\x00\x58", 2)  # standard fee limits
    return w
