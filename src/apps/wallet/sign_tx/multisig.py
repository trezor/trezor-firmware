from trezor.crypto import bip32
from trezor.crypto.hashlib import sha256
from trezor.messages import FailureType
from trezor.messages.HDNodePathType import HDNodePathType
from trezor.messages.MultisigRedeemScriptType import MultisigRedeemScriptType
from trezor.utils import HashWriter

from apps.wallet.sign_tx.writers import write_bytes, write_uint32


class MultisigError(ValueError):
    pass


class MultisigFingerprint:
    def __init__(self):
        self.fingerprint = None  # multisig fingerprint bytes
        self.mismatch = False  # flag if multisig input fingerprints are equal

    def add(self, multisig: MultisigRedeemScriptType):
        fp = multisig_fingerprint(multisig)
        assert fp is not None
        if self.fingerprint is None:
            self.fingerprint = fp
        elif self.fingerprint != fp:
            self.mismatch = True

    def matches(self, multisig: MultisigRedeemScriptType):
        fp = multisig_fingerprint(multisig)
        assert fp is not None
        if self.mismatch is False and self.fingerprint == fp:
            return True
        else:
            return False


def multisig_fingerprint(multisig: MultisigRedeemScriptType) -> bytes:
    pubkeys = multisig.pubkeys
    m = multisig.m
    n = len(pubkeys)

    if n < 1 or n > 15 or m < 1 or m > 15:
        raise MultisigError(FailureType.DataError, "Invalid multisig parameters")

    for hd in pubkeys:
        d = hd.node
        if len(d.public_key) != 33 or len(d.chain_code) != 32:
            raise MultisigError(FailureType.DataError, "Invalid multisig parameters")

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
    raise MultisigError(FailureType.DataError, "Pubkey not found in multisig script")


def multisig_get_pubkey(hd: HDNodePathType) -> bytes:
    p = hd.address_n
    n = hd.node
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
    return [multisig_get_pubkey(hd) for hd in multisig.pubkeys]
