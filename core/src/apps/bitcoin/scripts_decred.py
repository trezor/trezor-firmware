from trezor import utils, wire
from trezor.crypto import base58
from trezor.crypto.base58 import blake256d_32
from trezor.enums import InputScriptType

from apps.common.writers import write_bytes_fixed, write_uint64_le

from . import scripts
from .multisig import multisig_get_pubkeys, multisig_pubkey_index
from .scripts import (  # noqa: F401
    output_script_multisig,
    output_script_p2pkh,
    output_script_paytoopreturn,
)
from .writers import write_op_push

if False:
    from trezor.messages import MultisigRedeemScriptType

    from apps.common.coininfo import CoinInfo


def input_derive_script(
    script_type: InputScriptType,
    multisig: MultisigRedeemScriptType | None,
    coin: CoinInfo,
    hash_type: int,
    pubkey: bytes,
    signature: bytes,
) -> bytes:
    if script_type == InputScriptType.SPENDADDRESS:
        # p2pkh or p2sh
        return scripts.input_script_p2pkh_or_p2sh(pubkey, signature, hash_type)
    elif script_type == InputScriptType.SPENDMULTISIG:
        # p2sh multisig
        assert multisig is not None  # checked in sanitize_tx_input
        signature_index = multisig_pubkey_index(multisig, pubkey)
        return input_script_multisig(
            multisig, signature, signature_index, hash_type, coin
        )
    else:
        raise wire.ProcessError("Invalid script type")


def input_script_multisig(
    multisig: MultisigRedeemScriptType,
    signature: bytes,
    signature_index: int,
    hash_type: int,
    coin: CoinInfo,
) -> bytearray:
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
        total_length += 1 + len(s) + 1  # length, signature, hash_type
    total_length += 1 + redeem_script_length  # length, script

    w = utils.empty_bytearray(total_length)

    for s in signatures:
        if len(s):
            scripts.append_signature(w, s, hash_type)

    # redeem script
    write_op_push(w, redeem_script_length)
    scripts.write_output_script_multisig(w, pubkeys, multisig.m)

    return w


# A ticket purchase submission for an address hash.
def output_script_sstxsubmissionpkh(addr: str) -> bytearray:
    try:
        raw_address = base58.decode_check(addr, blake256d_32)
    except ValueError:
        raise wire.DataError("Invalid address")

    w = utils.empty_bytearray(26)
    w.append(0xBA)  # OP_SSTX
    w.append(0x76)  # OP_DUP
    w.append(0xA9)  # OP_HASH160
    w.append(0x14)  # OP_DATA_20
    write_bytes_fixed(w, raw_address[2:], 20)
    w.append(0x88)  # OP_EQUALVERIFY
    w.append(0xAC)  # OP_CHECKSIG
    return w


# Ticket purchase change script.
def output_script_sstxchange(addr: str) -> bytearray:
    try:
        raw_address = base58.decode_check(addr, blake256d_32)
    except ValueError:
        raise wire.DataError("Invalid address")

    w = utils.empty_bytearray(26)
    w.append(0xBD)  # OP_SSTXCHANGE
    w.append(0x76)  # OP_DUP
    w.append(0xA9)  # OP_HASH160
    w.append(0x14)  # OP_DATA_20
    write_bytes_fixed(w, raw_address[2:], 20)
    w.append(0x88)  # OP_EQUALVERIFY
    w.append(0xAC)  # OP_CHECKSIG
    return w


# Spend from a stake revocation.
def output_script_ssrtx(pkh: bytes) -> bytearray:
    utils.ensure(len(pkh) == 20)
    s = bytearray(26)
    s[0] = 0xBC  # OP_SSRTX
    s[1] = 0x76  # OP_DUP
    s[2] = 0xA9  # OP_HASH160
    s[3] = 0x14  # OP_DATA_20
    s[4:24] = pkh
    s[24] = 0x88  # OP_EQUALVERIFY
    s[25] = 0xAC  # OP_CHECKSIG
    return s


# Spend from a stake generation.
def output_script_ssgen(pkh: bytes) -> bytearray:
    utils.ensure(len(pkh) == 20)
    s = bytearray(26)
    s[0] = 0xBB  # OP_SSGEN
    s[1] = 0x76  # OP_DUP
    s[2] = 0xA9  # OP_HASH160
    s[3] = 0x14  # OP_DATA_20
    s[4:24] = pkh
    s[24] = 0x88  # OP_EQUALVERIFY
    s[25] = 0xAC  # OP_CHECKSIG
    return s


# Retrieve pkh bytes from a stake commitment OPRETURN.
def sstxcommitment_pkh(pkh: bytes, amount: int) -> bytes:
    w = utils.empty_bytearray(30)
    write_bytes_fixed(w, pkh, 20)
    write_uint64_le(w, amount)
    write_bytes_fixed(w, b"\x00\x58", 2)  # standard fee limits
    return w
