from trezor.crypto.hashlib import sha256
from trezor.crypto import bip32

from trezor.messages.MultisigRedeemScriptType import MultisigRedeemScriptType
from trezor.messages.HDNodePathType import HDNodePathType

from apps.wallet.sign_tx.writers import *
from apps.common.hash_writer import *


def multisig_fingerprint(multisig: MultisigRedeemScriptType) -> bytes:
    pubkeys = multisig.pubkeys
    m = multisig.m
    n = len(pubkeys)

    if n < 1 or n > 15:
        return None
    if m < 1 or m > 15:
        return None

    for hd in pubkeys:
        d = hd.node
        if len(d.public_key) != 33:
            return None
        if len(d.chain_code) != 32:
            return None

    # casting to bytes(), sorting on bytearray() is not supported in MicroPython
    pubkeys = sorted(pubkeys, key=lambda hd: bytes(hd.node.public_key))

    h = HashWriter(sha256)
    write_uint32(h, m)
    write_uint32(h, n)
    for hd in pubkeys:
        d = hd.node
        write_uint32(h, d.depth)
        write_uint32(h, d.fingerprint)
        write_uint32(h, d.child_num)
        write_bytes(h, d.chain_code)
        write_bytes(h, d.public_key)

    return h.get_digest()


def multisig_pubkey_index(multisig: MultisigRedeemScriptType, pubkey: bytes) -> int:
    for i, hd in enumerate(multisig.pubkeys):
        if multisig_get_pubkey(hd) == pubkey:
            return i
    return -1


def multisig_get_pubkey(hd: HDNodePathType) -> bytes:
    p = hd.address_n
    n = hd.node
    node = bip32.HDNode(
        depth=n.depth,
        fingerprint=n.fingerprint,
        child_num=n.child_num,
        chain_code=n.chain_code,
        public_key=n.public_key)
    for i in p:
        node.derive(i, True)
    return node.public_key()


def multisig_get_pubkeys(multisig: MultisigRedeemScriptType):
    return [multisig_get_pubkey(hd) for hd in multisig.pubkeys]


def check_address_n_against_pubkeys(multisig: MultisigRedeemScriptType, address_n) -> bool:
    for p in multisig.pubkeys:
        if p.address_n == address_n:
            return True
    return False
