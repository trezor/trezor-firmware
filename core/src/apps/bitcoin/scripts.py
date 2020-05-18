from trezor import utils, wire
from trezor.crypto import base58, cashaddr
from trezor.crypto.hashlib import sha256
from trezor.messages import InputScriptType, OutputScriptType
from trezor.messages.MultisigRedeemScriptType import MultisigRedeemScriptType
from trezor.messages.TxInputType import TxInputType
from trezor.messages.TxOutputType import TxOutputType

from apps.common import address_type
from apps.common.coininfo import CoinInfo
from apps.common.writers import empty_bytearray, write_bitcoin_varint

from . import common
from .multisig import (
    multisig_get_pubkey_count,
    multisig_get_pubkeys,
    multisig_pubkey_index,
)
from .writers import write_bytes_fixed, write_bytes_unchecked, write_op_push

if False:
    from typing import List, Optional
    from .writers import Writer


def input_derive_script(
    txi: TxInputType,
    coin: CoinInfo,
    hash_type: int,
    pubkey: bytes,
    signature: Optional[bytes],
) -> bytes:
    if txi.script_type == InputScriptType.SPENDADDRESS:
        # p2pkh or p2sh
        return input_script_p2pkh_or_p2sh(pubkey, signature, hash_type)

    if txi.script_type == InputScriptType.SPENDP2SHWITNESS:
        # p2wpkh or p2wsh using p2sh

        if txi.multisig:
            # p2wsh in p2sh
            pubkeys = multisig_get_pubkeys(txi.multisig)
            witness_script_hasher = utils.HashWriter(sha256())
            write_output_script_multisig(witness_script_hasher, pubkeys, txi.multisig.m)
            witness_script_hash = witness_script_hasher.get_digest()
            return input_script_p2wsh_in_p2sh(witness_script_hash)

        # p2wpkh in p2sh
        return input_script_p2wpkh_in_p2sh(common.ecdsa_hash_pubkey(pubkey, coin))
    elif txi.script_type == InputScriptType.SPENDWITNESS:
        # native p2wpkh or p2wsh
        return input_script_native_p2wpkh_or_p2wsh()
    elif txi.script_type == InputScriptType.SPENDMULTISIG:
        # p2sh multisig
        signature_index = multisig_pubkey_index(txi.multisig, pubkey)
        return input_script_multisig(
            txi.multisig, signature, signature_index, hash_type, coin
        )
    else:
        raise wire.ProcessError("Invalid script type")


def output_derive_script(txo: TxOutputType, coin: CoinInfo) -> bytes:
    if txo.script_type == OutputScriptType.PAYTOOPRETURN:
        return output_script_paytoopreturn(txo.op_return_data)

    if coin.bech32_prefix and txo.address.startswith(coin.bech32_prefix):
        # p2wpkh or p2wsh
        witprog = common.decode_bech32_address(coin.bech32_prefix, txo.address)
        return output_script_native_p2wpkh_or_p2wsh(witprog)

    if (
        not utils.BITCOIN_ONLY
        and coin.cashaddr_prefix is not None
        and txo.address.startswith(coin.cashaddr_prefix + ":")
    ):
        prefix, addr = txo.address.split(":")
        version, data = cashaddr.decode(prefix, addr)
        if version == cashaddr.ADDRESS_TYPE_P2KH:
            version = coin.address_type
        elif version == cashaddr.ADDRESS_TYPE_P2SH:
            version = coin.address_type_p2sh
        else:
            raise wire.DataError("Unknown cashaddr address type")
        raw_address = bytes([version]) + data
    else:
        try:
            raw_address = base58.decode_check(txo.address, coin.b58_hash)
        except ValueError:
            raise wire.DataError("Invalid address")

    if address_type.check(coin.address_type, raw_address):
        # p2pkh
        pubkeyhash = address_type.strip(coin.address_type, raw_address)
        script = output_script_p2pkh(pubkeyhash)
        return script
    elif address_type.check(coin.address_type_p2sh, raw_address):
        # p2sh
        scripthash = address_type.strip(coin.address_type_p2sh, raw_address)
        script = output_script_p2sh(scripthash)
        return script

    raise wire.DataError("Invalid address type")


# see https://github.com/bitcoin/bips/blob/master/bip-0143.mediawiki#specification
# item 5 for details
def bip143_derive_script_code(txi: TxInputType, pubkeyhash: bytes) -> bytearray:

    if txi.multisig:
        return output_script_multisig(
            multisig_get_pubkeys(txi.multisig), txi.multisig.m
        )

    p2pkh = (
        txi.script_type == InputScriptType.SPENDWITNESS
        or txi.script_type == InputScriptType.SPENDP2SHWITNESS
        or txi.script_type == InputScriptType.SPENDADDRESS
    )
    if p2pkh:
        # for p2wpkh in p2sh or native p2wpkh
        # the scriptCode is a classic p2pkh
        return output_script_p2pkh(pubkeyhash)

    else:
        raise wire.DataError("Unknown input script type for bip143 script code")


# P2PKH, P2SH
# ===
# https://github.com/bitcoin/bips/blob/master/bip-0016.mediawiki


def input_script_p2pkh_or_p2sh(
    pubkey: bytes, signature: bytes, sighash: int
) -> bytearray:
    w = empty_bytearray(5 + len(signature) + 1 + 5 + len(pubkey))
    append_signature(w, signature, sighash)
    append_pubkey(w, pubkey)
    return w


def output_script_p2pkh(pubkeyhash: bytes) -> bytearray:
    utils.ensure(len(pubkeyhash) == 20)
    s = bytearray(25)
    s[0] = 0x76  # OP_DUP
    s[1] = 0xA9  # OP_HASH_160
    s[2] = 0x14  # pushing 20 bytes
    s[3:23] = pubkeyhash
    s[23] = 0x88  # OP_EQUALVERIFY
    s[24] = 0xAC  # OP_CHECKSIG
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


# SegWit: Native P2WPKH or P2WSH
# ===
# https://github.com/bitcoin/bips/blob/master/bip-0141.mediawiki#p2wpkh
# https://github.com/bitcoin/bips/blob/master/bip-0141.mediawiki#p2wsh
#
# P2WPKH (Pay-to-Witness-Public-Key-Hash) is the segwit native P2PKH.
# Not backwards compatible.
#
# P2WSH (Pay-to-Witness-Script-Hash) is segwit native P2SH.
# Not backwards compatible.


def input_script_native_p2wpkh_or_p2wsh() -> bytearray:
    # Completely replaced by the witness and therefore empty.
    return bytearray(0)


def output_script_native_p2wpkh_or_p2wsh(witprog: bytes) -> bytearray:
    # Either:
    # 00 14 <20-byte-key-hash>
    # 00 20 <32-byte-script-hash>
    length = len(witprog)
    utils.ensure(length == 20 or length == 32)

    w = empty_bytearray(3 + length)
    w.append(0x00)  # witness version byte
    w.append(length)  # pub key hash length is 20 (P2WPKH) or 32 (P2WSH) bytes
    write_bytes_fixed(w, witprog, length)  # pub key hash
    return w


# SegWit: P2WPKH nested in P2SH
# ===
# https://github.com/bitcoin/bips/blob/master/bip-0141.mediawiki#witness-program
#
# P2WPKH is nested in P2SH to be backwards compatible.
# Uses normal P2SH output scripts.


def input_script_p2wpkh_in_p2sh(pubkeyhash: bytes) -> bytearray:
    # 16 00 14 <pubkeyhash>
    # Signature is moved to the witness.
    utils.ensure(len(pubkeyhash) == 20)

    w = empty_bytearray(3 + len(pubkeyhash))
    w.append(0x16)  # length of the data
    w.append(0x00)  # witness version byte
    w.append(0x14)  # P2WPKH witness program (pub key hash length)
    write_bytes_fixed(w, pubkeyhash, 20)  # pub key hash
    return w


# SegWit: P2WSH nested in P2SH
# ===
# https://github.com/bitcoin/bips/blob/master/bip-0141.mediawiki#p2wsh-nested-in-bip16-p2sh
#
# P2WSH is nested in P2SH to be backwards compatible.
# Uses normal P2SH output scripts.


def input_script_p2wsh_in_p2sh(script_hash: bytes) -> bytearray:
    # 22 00 20 <redeem script hash>
    # Signature is moved to the witness.

    if len(script_hash) != 32:
        raise wire.DataError("Redeem script hash should be 32 bytes long")

    w = empty_bytearray(3 + len(script_hash))
    w.append(0x22)  # length of the data
    w.append(0x00)  # witness version byte
    w.append(0x20)  # P2WSH witness program (redeem script hash length)
    write_bytes_fixed(w, script_hash, 32)
    return w


# SegWit: Witness getters
# ===


def witness_p2wpkh(signature: bytes, pubkey: bytes, sighash: int) -> bytearray:
    w = empty_bytearray(1 + 5 + len(signature) + 1 + 5 + len(pubkey))
    write_bitcoin_varint(w, 0x02)  # num of segwit items, in P2WPKH it's always 2
    append_signature(w, signature, sighash)
    append_pubkey(w, pubkey)
    return w


def witness_p2wsh(
    multisig: MultisigRedeemScriptType,
    signature: bytes,
    signature_index: int,
    sighash: int,
) -> bytearray:
    # get other signatures, stretch with None to the number of the pubkeys
    signatures = multisig.signatures + [None] * (
        multisig_get_pubkey_count(multisig) - len(multisig.signatures)
    )
    # fill in our signature
    if signatures[signature_index]:
        raise wire.DataError("Invalid multisig parameters")
    signatures[signature_index] = signature

    # filter empty
    signatures = [s for s in signatures if s]

    # witness program + signatures + redeem script
    num_of_witness_items = 1 + len(signatures) + 1

    # length of the redeem script
    pubkeys = multisig_get_pubkeys(multisig)
    redeem_script_length = output_script_multisig_length(pubkeys, multisig.m)

    # length of the result
    total_length = 1 + 1  # number of items, OP_FALSE
    for s in signatures:
        total_length += 1 + len(s) + 1  # length, signature, sighash
    total_length += 1 + redeem_script_length  # length, script

    w = empty_bytearray(total_length)

    write_bitcoin_varint(w, num_of_witness_items)
    # Starts with OP_FALSE because of an old OP_CHECKMULTISIG bug, which
    # consumes one additional item on the stack:
    # https://bitcoin.org/en/developer-guide#standard-transactions
    write_bitcoin_varint(w, 0)

    for s in signatures:
        append_signature(w, s, sighash)  # size of the witness included

    # redeem script
    write_bitcoin_varint(w, redeem_script_length)
    write_output_script_multisig(w, pubkeys, multisig.m)

    return w


# Multisig
# ===
#
# Used either as P2SH, P2WSH, or P2WSH nested in P2SH.


def input_script_multisig(
    multisig: MultisigRedeemScriptType,
    signature: bytes,
    signature_index: int,
    sighash: int,
    coin: CoinInfo,
) -> bytearray:
    signatures = multisig.signatures  # other signatures
    if len(signatures[signature_index]) > 0:
        raise wire.DataError("Invalid multisig parameters")
    signatures[signature_index] = signature  # our signature

    # length of the redeem script
    pubkeys = multisig_get_pubkeys(multisig)
    redeem_script_length = output_script_multisig_length(pubkeys, multisig.m)

    # length of the result
    total_length = 0
    if utils.BITCOIN_ONLY or not coin.decred:
        total_length += 1  # OP_FALSE
    for s in signatures:
        total_length += 1 + len(s) + 1  # length, signature, sighash
    total_length += 1 + redeem_script_length  # length, script

    w = empty_bytearray(total_length)

    if utils.BITCOIN_ONLY or not coin.decred:
        # Starts with OP_FALSE because of an old OP_CHECKMULTISIG bug, which
        # consumes one additional item on the stack:
        # https://bitcoin.org/en/developer-guide#standard-transactions
        w.append(0x00)

    for s in signatures:
        if len(s):
            append_signature(w, s, sighash)

    # redeem script
    write_op_push(w, redeem_script_length)
    write_output_script_multisig(w, pubkeys, multisig.m)

    return w


def output_script_multisig(pubkeys: List[bytes], m: int) -> bytearray:
    w = empty_bytearray(output_script_multisig_length(pubkeys, m))
    write_output_script_multisig(w, pubkeys, m)
    return w


def write_output_script_multisig(w: Writer, pubkeys: List[bytes], m: int) -> None:
    n = len(pubkeys)
    if n < 1 or n > 15 or m < 1 or m > 15 or m > n:
        raise wire.DataError("Invalid multisig parameters")
    for pubkey in pubkeys:
        if len(pubkey) != 33:
            raise wire.DataError("Invalid multisig parameters")

    w.append(0x50 + m)  # numbers 1 to 16 are pushed as 0x50 + value
    for p in pubkeys:
        append_pubkey(w, p)
    w.append(0x50 + n)
    w.append(0xAE)  # OP_CHECKMULTISIG


def output_script_multisig_length(pubkeys: List[bytes], m: int) -> int:
    return 1 + len(pubkeys) * (1 + 33) + 1 + 1  # see output_script_multisig


# OP_RETURN
# ===


def output_script_paytoopreturn(data: bytes) -> bytearray:
    w = empty_bytearray(1 + 5 + len(data))
    w.append(0x6A)  # OP_RETURN
    write_op_push(w, len(data))
    w.extend(data)
    return w


# Helpers
# ===


def append_signature(w: Writer, signature: bytes, sighash: int) -> None:
    write_op_push(w, len(signature) + 1)
    write_bytes_unchecked(w, signature)
    w.append(sighash)


def append_pubkey(w: Writer, pubkey: bytes) -> None:
    write_op_push(w, len(pubkey))
    write_bytes_unchecked(w, pubkey)
