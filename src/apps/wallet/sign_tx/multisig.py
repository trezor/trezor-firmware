from trezor.crypto import bip32
from trezor.crypto.hashlib import sha256
from trezor.messages import FailureType
from trezor.messages.HDNodeType import HDNodeType
from trezor.messages.MultisigRedeemScriptType import MultisigRedeemScriptType
from trezor.utils import HashWriter, ensure

from apps.wallet.sign_tx.writers import write_bytes, write_uint32


class MultisigError(ValueError):
    pass


class MultisigFingerprint:
    def __init__(self):
        self.fingerprint = None  # multisig fingerprint bytes
        self.mismatch = False  # flag if multisig input fingerprints are equal

    def add(self, multisig: MultisigRedeemScriptType):
        fp = multisig_fingerprint(multisig)
        ensure(fp is not None)
        if self.fingerprint is None:
            self.fingerprint = fp
        elif self.fingerprint != fp:
            self.mismatch = True

    def matches(self, multisig: MultisigRedeemScriptType):
        fp = multisig_fingerprint(multisig)
        ensure(fp is not None)
        if self.mismatch is False and self.fingerprint == fp:
            return True
        else:
            return False


def multisig_fingerprint(multisig: MultisigRedeemScriptType) -> bytes:
    if multisig.nodes:
        pubnodes = multisig.nodes
    else:
        pubnodes = [hd.node for hd in multisig.pubkeys]
    m = multisig.m
    n = len(pubnodes)

    if n < 1 or n > 15 or m < 1 or m > 15:
        raise MultisigError(FailureType.DataError, "Invalid multisig parameters")

    for d in pubnodes:
        if len(d.public_key) != 33 or len(d.chain_code) != 32:
            raise MultisigError(FailureType.DataError, "Invalid multisig parameters")

    # casting to bytes(), sorting on bytearray() is not supported in MicroPython
    pubnodes = sorted(pubnodes, key=lambda n: bytes(n.public_key))

    h = HashWriter(sha256())
    write_uint32(h, m)
    write_uint32(h, n)
    for d in pubnodes:
        write_uint32(h, d.depth)
        write_uint32(h, d.fingerprint)
        write_uint32(h, d.child_num)
        write_bytes(h, d.chain_code)
        write_bytes(h, d.public_key)

    return h.get_digest()


def multisig_pubkey_index(multisig: MultisigRedeemScriptType, pubkey: bytes) -> int:
    if multisig.nodes:
        for i, hd in enumerate(multisig.nodes):
            if multisig_get_pubkey(hd, multisig.address_n) == pubkey:
                return i
    else:
        for i, hd in enumerate(multisig.pubkeys):
            if multisig_get_pubkey(hd.node, hd.address_n) == pubkey:
                return i
    raise MultisigError(FailureType.DataError, "Pubkey not found in multisig script")


def multisig_get_pubkey(n: HDNodeType, p: list) -> bytes:
    node = bip32.HDNode(
        depth=n.depth,
        fingerprint=n.fingerprint,
        child_num=n.child_num,
        chain_code=n.chain_code,
        public_key=n.public_key,
    )
    for i in p:
        node.derive(i, True)
    return node.public_key()


def multisig_get_pubkeys(multisig: MultisigRedeemScriptType):
    if multisig.nodes:
        return [multisig_get_pubkey(hd, multisig.address_n) for hd in multisig.nodes]
    else:
        return [multisig_get_pubkey(hd.node, hd.address_n) for hd in multisig.pubkeys]


def multisig_get_pubkey_count(multisig: MultisigRedeemScriptType):
    if multisig.nodes:
        return len(multisig.nodes)
    else:
        len(multisig.pubkeys)
