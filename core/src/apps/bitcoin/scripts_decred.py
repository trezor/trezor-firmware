from micropython import const
from typing import TYPE_CHECKING

from trezor import utils
from trezor.crypto import base58
from trezor.crypto.base58 import blake256d_32
from trezor.enums import DecredStakingSpendType
from trezor.wire import DataError

from . import scripts
from .scripts import (  # noqa: F401
    output_script_paytoopreturn,
    write_output_script_multisig,
    write_output_script_p2pkh,
)
from .writers import write_compact_size

# These are decred specific opcodes related to staking.
_OP_SSTX = const(0xBA)
_OP_SSGEN = const(0xBB)
_OP_SSRTX = const(0xBC)
_OP_SSTXCHANGE = const(0xBD)

_STAKE_TREE = const(1)

if TYPE_CHECKING:
    from trezor.enums import InputScriptType
    from trezor.messages import MultisigRedeemScriptType

    from apps.common.coininfo import CoinInfo

    from .common import SigHashType
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
    from trezor import wire
    from trezor.enums import InputScriptType

    from .multisig import multisig_pubkey_index

    if script_type == InputScriptType.SPENDADDRESS:
        # p2pkh or p2sh
        scripts.write_input_script_p2pkh_or_p2sh_prefixed(
            w, pubkey, signature, sighash_type
        )
    elif script_type == InputScriptType.SPENDMULTISIG:
        # p2sh multisig
        assert multisig is not None  # checked in _sanitize_tx_input
        signature_index = multisig_pubkey_index(multisig, pubkey)
        _write_input_script_multisig_prefixed(
            w, multisig, signature, signature_index, sighash_type, coin
        )
    else:
        raise wire.ProcessError("Invalid script type")


def _write_input_script_multisig_prefixed(
    w: Writer,
    multisig: MultisigRedeemScriptType,
    signature: bytes,
    signature_index: int,
    sighash_type: SigHashType,
    coin: CoinInfo,
) -> None:
    from .multisig import multisig_get_pubkeys
    from .writers import op_push_length, write_op_push

    signatures = multisig.signatures  # other signatures
    if len(signatures[signature_index]) > 0:
        raise DataError("Invalid multisig parameters")
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
    write_compact_size(w, total_length)

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
        raise DataError("Invalid address")

    w = utils.empty_bytearray(26)
    w.append(_OP_SSTX)
    scripts.write_output_script_p2pkh(w, raw_address[2:])
    return w


# Ticket purchase change script.
def output_script_sstxchange(addr: str) -> bytearray:
    try:
        raw_address = base58.decode_check(addr, blake256d_32)
    except ValueError:
        raise DataError("Invalid address")

    w = utils.empty_bytearray(26)
    w.append(_OP_SSTXCHANGE)
    scripts.write_output_script_p2pkh(w, raw_address[2:])
    return w


# Spend from a stake revocation.
def write_output_script_ssrtx_prefixed(w: Writer, pkh: bytes) -> None:
    utils.ensure(len(pkh) == 20)
    write_compact_size(w, 26)
    w.append(_OP_SSRTX)
    scripts.write_output_script_p2pkh(w, pkh)


# Spend from a stake generation.
def write_output_script_ssgen_prefixed(w: Writer, pkh: bytes) -> None:
    utils.ensure(len(pkh) == 20)
    write_compact_size(w, 26)
    w.append(_OP_SSGEN)
    scripts.write_output_script_p2pkh(w, pkh)


# Stake commitment OPRETURN.
def sstxcommitment_pkh(pkh: bytes, amount: int) -> bytes:
    from apps.common.writers import write_bytes_fixed, write_uint64_le

    w = utils.empty_bytearray(30)
    write_bytes_fixed(w, pkh, 20)
    write_uint64_le(w, amount)
    write_bytes_fixed(w, b"\x00\x58", 2)  # standard fee limits
    return w


def output_script_p2pkh(pubkeyhash: bytes) -> bytearray:
    s = utils.empty_bytearray(25)
    scripts.write_output_script_p2pkh(s, pubkeyhash)
    return s


def output_script_p2sh(scripthash: bytes) -> bytearray:
    # A9 14 <scripthash> 87
    utils.ensure(len(scripthash) == 20)
    s = bytearray(23)
    s[0] = 0xA9  # OP_HASH_160
    s[1] = 0x14  # pushing 20 bytes
    s[2:22] = scripthash
    s[22] = 0x87  # OP_EQUAL
    return s


def output_derive_script(
    tree: int | None, stakeType: int | None, addr: str, coin: CoinInfo
) -> bytes:
    from trezor.crypto import base58

    from apps.common import address_type

    try:
        raw_address = base58.decode_check(addr, blake256d_32)
    except ValueError:
        raise DataError("Invalid address")

    isStakeOutput = False
    if tree is not None:
        if stakeType is not None:
            if tree == _STAKE_TREE:
                isStakeOutput = True

    if isStakeOutput:
        assert stakeType is not None
        if stakeType == DecredStakingSpendType.SSGen:
            script = utils.empty_bytearray(26)
            script.append(_OP_SSGEN)
            scripts.write_output_script_p2pkh(script, raw_address[2:])
            return script
        elif stakeType == DecredStakingSpendType.SSRTX:
            script = utils.empty_bytearray(26)
            script.append(_OP_SSRTX)
            scripts.write_output_script_p2pkh(script, raw_address[2:])
            return script

    elif address_type.check(coin.address_type, raw_address):
        # p2pkh
        pubkeyhash = address_type.strip(coin.address_type, raw_address)
        script = output_script_p2pkh(pubkeyhash)
        return script
    elif address_type.check(coin.address_type_p2sh, raw_address):
        scripthash = address_type.strip(coin.address_type_p2sh, raw_address)
        script = output_script_p2sh(scripthash)
        return script

    raise DataError("Invalid address type")
