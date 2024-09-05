from typing import TYPE_CHECKING

from trezor.enums import MultisigPubkeysOrder
from trezor.wire import DataError

if TYPE_CHECKING:
    from trezor.messages import HDNodeType, MultisigRedeemScriptType

    from apps.common import paths


def multisig_fingerprint(multisig: MultisigRedeemScriptType) -> bytes:
    from trezor.crypto.hashlib import sha256
    from trezor.utils import HashWriter

    from .writers import write_bytes_fixed, write_uint32

    if multisig.nodes:
        pubnodes = multisig.nodes
    else:
        pubnodes = [hd.node for hd in multisig.pubkeys]
    m = multisig.m
    n = len(pubnodes)

    if n < 1 or n > 15 or m < 1 or m > 15:
        raise DataError("Invalid multisig parameters")

    for d in pubnodes:
        if len(d.public_key) != 33 or len(d.chain_code) != 32:
            raise DataError("Invalid multisig parameters")

    if multisig.pubkeys_order == MultisigPubkeysOrder.LEXICOGRAPHIC:
        # If the order of pubkeys is lexicographic, we don't want the fingerprint to depend on the order of the pubnodes, so we sort the pubnodes before hashing.
        pubnodes.sort(key=lambda n: n.public_key + n.chain_code)

    h = HashWriter(sha256())
    write_uint32(h, m)
    write_uint32(h, n)
    write_uint32(h, multisig.pubkeys_order)
    for d in pubnodes:
        write_uint32(h, d.depth)
        write_uint32(h, d.fingerprint)
        write_uint32(h, d.child_num)
        write_bytes_fixed(h, d.chain_code, 32)
        write_bytes_fixed(h, d.public_key, 33)

    return h.get_digest()


def validate_multisig(multisig: MultisigRedeemScriptType) -> None:
    from apps.common import paths

    if any(paths.is_hardened(n) for n in multisig.address_n):
        raise DataError("Cannot perform hardened derivation from XPUB")
    for hd in multisig.pubkeys:
        if any(paths.is_hardened(n) for n in hd.address_n):
            raise DataError("Cannot perform hardened derivation from XPUB")


def multisig_pubkey_index(multisig: MultisigRedeemScriptType, pubkey: bytes) -> int:
    validate_multisig(multisig)
    if multisig.nodes:
        for i, hd_node in enumerate(multisig.nodes):
            if multisig_get_pubkey(hd_node, multisig.address_n) == pubkey:
                return i
    else:
        for i, hd in enumerate(multisig.pubkeys):
            if multisig_get_pubkey(hd.node, hd.address_n) == pubkey:
                return i
    raise DataError("Pubkey not found in multisig script")


def multisig_get_pubkey(n: HDNodeType, p: paths.Bip32Path) -> bytes:
    from trezor.crypto import bip32

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


def multisig_get_dummy_pubkey(multisig: MultisigRedeemScriptType) -> bytes:
    from trezor.crypto import bip32

    # The following encodes this xpub into an HDNode. It is the NUMS point suggested
    # in BIP341, with a chaincode of 32 0 bytes. Deriving a pubkey from this node
    # results in a provably unspendable pubkey.
    # https://delvingbitcoin.org/t/unspendable-keys-in-descriptors/304
    # xpub661MyMwAqRbcEYS8w7XLSVeEsBXy79zSzH1J8vCdxAZningWLdN3zgtU6QgnecKFpJFPpdzxKrwoaZoV44qAJewsc4kX9vGaCaBExuvJH57
    node = bip32.HDNode(
        depth=0,
        fingerprint=2084970077,
        child_num=0,
        chain_code=b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
        public_key=b"\x02P\x92\x9bt\xc1\xa0IT\xb7\x8bK`5\xe9z^\x07\x8aZ\x0f(\xec\x96\xd5G\xbf\xee\x9a\xce\x80:\xc0",
    )

    for i in multisig.address_n:
        node.derive(i, True)
    return node.public_key()


def multisig_get_pubkeys(multisig: MultisigRedeemScriptType) -> list[bytes]:
    validate_multisig(multisig)
    if multisig.nodes:
        pubkeys = [multisig_get_pubkey(hd, multisig.address_n) for hd in multisig.nodes]
    else:
        pubkeys = [
            multisig_get_pubkey(hd.node, hd.address_n) for hd in multisig.pubkeys
        ]
    if multisig.pubkeys_order == MultisigPubkeysOrder.LEXICOGRAPHIC:
        pubkeys.sort()
    return pubkeys


def multisig_get_pubkey_count(multisig: MultisigRedeemScriptType) -> int:
    if multisig.nodes:
        return len(multisig.nodes)
    else:
        return len(multisig.pubkeys)
