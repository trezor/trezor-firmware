from trezor import utils
from trezor.messages.MultisigRedeemScriptType import MultisigRedeemScriptType

from apps.common.coininfo import CoinInfo
from apps.common.writers import empty_bytearray
from apps.wallet.sign_tx.multisig import multisig_get_pubkey_count, multisig_get_pubkeys
from apps.wallet.sign_tx.writers import (
    write_bytes,
    write_op_push,
    write_scriptnum,
    write_varint,
)


class ScriptsError(ValueError):
    pass


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


def script_replay_protection_bip115(
    block_hash: bytes, block_height: bytes
) -> bytearray:
    if block_hash is None or block_height is None:
        return bytearray()
    utils.ensure(len(block_hash) == 32)
    s = bytearray(33)
    s[0] = 0x20  # 32 bytes for block hash
    s[1:33] = block_hash  # block hash
    write_scriptnum(s, block_height)
    s.append(0xB4)  # OP_CHECKBLOCKATHEIGHT
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
    utils.ensure(len(witprog) == 20 or len(witprog) == 32)

    w = empty_bytearray(3 + len(witprog))
    w.append(0x00)  # witness version byte
    w.append(len(witprog))  # pub key hash length is 20 (P2WPKH) or 32 (P2WSH) bytes
    write_bytes(w, witprog)  # pub key hash
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
    write_bytes(w, pubkeyhash)  # pub key hash
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
        raise ScriptsError("Redeem script hash should be 32 bytes long")

    w = empty_bytearray(3 + len(script_hash))
    w.append(0x22)  # length of the data
    w.append(0x00)  # witness version byte
    w.append(0x20)  # P2WSH witness program (redeem script hash length)
    write_bytes(w, script_hash)
    return w


# SegWit: Witness getters
# ===


def witness_p2wpkh(signature: bytes, pubkey: bytes, sighash: int):
    w = empty_bytearray(1 + 5 + len(signature) + 1 + 5 + len(pubkey))
    write_varint(w, 0x02)  # num of segwit items, in P2WPKH it's always 2
    append_signature(w, signature, sighash)
    append_pubkey(w, pubkey)
    return w


def witness_p2wsh(
    multisig: MultisigRedeemScriptType,
    signature: bytes,
    signature_index: int,
    sighash: int,
):
    # get other signatures, stretch with None to the number of the pubkeys
    signatures = multisig.signatures + [None] * (
        multisig_get_pubkey_count(multisig) - len(multisig.signatures)
    )
    # fill in our signature
    if signatures[signature_index]:
        raise ScriptsError("Invalid multisig parameters")
    signatures[signature_index] = signature

    # filter empty
    signatures = [s for s in signatures if s]

    # witness program + signatures + redeem script
    num_of_witness_items = 1 + len(signatures) + 1

    # length of the redeem script
    pubkeys = multisig_get_pubkeys(multisig)
    redeem_script_length = output_script_multisig_length(pubkeys, multisig.m)

    # length of the result
    total_length = 1 + 1  # number of items, version
    for s in signatures:
        total_length += 1 + len(s) + 1  # length, signature, sighash
    total_length += 1 + redeem_script_length  # length, script

    w = empty_bytearray(total_length)

    write_varint(w, num_of_witness_items)
    write_varint(w, 0)  # version 0 witness program

    for s in signatures:
        append_signature(w, s, sighash)  # size of the witness included

    # redeem script
    write_varint(w, redeem_script_length)
    output_script_multisig(pubkeys, multisig.m, w)

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
        raise ScriptsError("Invalid multisig parameters")
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

    if not coin.decred:
        # Starts with OP_FALSE because of an old OP_CHECKMULTISIG bug, which
        # consumes one additional item on the stack:
        # https://bitcoin.org/en/developer-guide#standard-transactions
        w.append(0x00)

    for s in signatures:
        if len(s):
            append_signature(w, s, sighash)

    # redeem script
    write_op_push(w, redeem_script_length)
    output_script_multisig(pubkeys, multisig.m, w)

    return w


def output_script_multisig(pubkeys, m: int, w: bytearray = None) -> bytearray:
    n = len(pubkeys)
    if n < 1 or n > 15 or m < 1 or m > 15 or m > n:
        raise ScriptsError("Invalid multisig parameters")
    for pubkey in pubkeys:
        if len(pubkey) != 33:
            raise ScriptsError("Invalid multisig parameters")

    if w is None:
        w = empty_bytearray(output_script_multisig_length(pubkeys, m))
    w.append(0x50 + m)  # numbers 1 to 16 are pushed as 0x50 + value
    for p in pubkeys:
        append_pubkey(w, p)
    w.append(0x50 + n)
    w.append(0xAE)  # OP_CHECKMULTISIG
    return w


def output_script_multisig_length(pubkeys, m: int) -> int:
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


def append_signature(w: bytearray, signature: bytes, sighash: int) -> bytearray:
    write_op_push(w, len(signature) + 1)
    write_bytes(w, signature)
    w.append(sighash)
    return w


def append_pubkey(w: bytearray, pubkey: bytes) -> bytearray:
    write_op_push(w, len(pubkey))
    write_bytes(w, pubkey)
    return w
