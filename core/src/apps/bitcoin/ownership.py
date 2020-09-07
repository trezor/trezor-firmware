from trezor import utils, wire
from trezor.crypto import bip32, hashlib, hmac

from apps.common.keychain import Keychain
from apps.common.readers import read_bitcoin_varint
from apps.common.writers import (
    empty_bytearray,
    write_bitcoin_varint,
    write_bytes_fixed,
    write_uint8,
)

from . import common
from .scripts import read_bip322_signature_proof, write_bip322_signature_proof
from .verification import SignatureVerifier

if False:
    from typing import List, Optional, Tuple
    from trezor.messages.MultisigRedeemScriptType import MultisigRedeemScriptType
    from trezor.messages.TxInputType import EnumTypeInputScriptType
    from apps.common.coininfo import CoinInfo

# This module implements the SLIP-0019 proof of ownership format.

_VERSION_MAGIC = b"SL\x00\x19"
_FLAG_USER_CONFIRMED = 0x01
_OWNERSHIP_ID_LEN = 32
_OWNERSHIP_ID_KEY_PATH = [b"SLIP-0019", b"Ownership identification key"]


def generate_proof(
    node: bip32.HDNode,
    script_type: EnumTypeInputScriptType,
    multisig: MultisigRedeemScriptType,
    coin: CoinInfo,
    user_confirmed: bool,
    ownership_ids: List[bytes],
    script_pubkey: bytes,
    commitment_data: Optional[bytes],
) -> Tuple[bytes, bytes]:
    flags = 0
    if user_confirmed:
        flags |= _FLAG_USER_CONFIRMED

    proof = empty_bytearray(4 + 1 + 1 + len(ownership_ids) * _OWNERSHIP_ID_LEN)

    write_bytes_fixed(proof, _VERSION_MAGIC, 4)
    write_uint8(proof, flags)
    write_bitcoin_varint(proof, len(ownership_ids))
    for ownership_id in ownership_ids:
        write_bytes_fixed(proof, ownership_id, _OWNERSHIP_ID_LEN)

    sighash = hashlib.sha256(proof)
    sighash.update(script_pubkey)
    if commitment_data:
        sighash.update(commitment_data)
    signature = common.ecdsa_sign(node, sighash.digest())
    public_key = node.public_key()
    write_bip322_signature_proof(
        proof, script_type, multisig, coin, public_key, signature
    )

    return proof, signature


def verify_nonownership(
    proof: bytes,
    script_pubkey: bytes,
    commitment_data: Optional[bytes],
    keychain: Keychain,
    coin: CoinInfo,
) -> bool:
    try:
        r = utils.BufferReader(proof)
        if r.read(4) != _VERSION_MAGIC:
            raise wire.DataError("Unknown format of proof of ownership")

        flags = r.get()
        if flags & 0b1111_1110:
            raise wire.DataError("Unknown flags in proof of ownership")

        # Determine whether our ownership ID appears in the proof.
        id_count = read_bitcoin_varint(r)
        ownership_id = get_identifier(script_pubkey, keychain)
        not_owned = True
        for _ in range(id_count):
            if utils.consteq(ownership_id, r.read(_OWNERSHIP_ID_LEN)):
                not_owned = False

        # Verify the BIP-322 SignatureProof.

        proof_body = proof[: r.offset]
        sighash = hashlib.sha256(proof_body)
        sighash.update(script_pubkey)
        if commitment_data:
            sighash.update(commitment_data)
        script_sig, witness = read_bip322_signature_proof(r)

        # We don't call verifier.ensure_hash_type() to avoid possible compatibility
        # issues between implementations, because the hash type doesn't influence
        # the digest and the value to use is not defined in BIP-322.
        verifier = SignatureVerifier(script_pubkey, script_sig, witness, coin)
        verifier.verify(sighash.digest())
    except (ValueError, EOFError):
        raise wire.DataError("Invalid proof of ownership")

    return not_owned


def get_identifier(script_pubkey: bytes, keychain: Keychain) -> bytes:
    # k = Key(m/"SLIP-0019"/"Ownership identification key")
    node = keychain.derive_slip21(_OWNERSHIP_ID_KEY_PATH)

    # id = HMAC-SHA256(key = k, msg = scriptPubKey)
    return hmac.Hmac(node.key(), script_pubkey, hashlib.sha256).digest()
