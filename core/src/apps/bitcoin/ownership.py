from micropython import const
from typing import TYPE_CHECKING

from trezor import utils
from trezor.crypto.hashlib import sha256
from trezor.utils import HashWriter
from trezor.wire import DataError

from apps.bitcoin.writers import write_bytes_prefixed
from apps.common.readers import read_compact_size

from .scripts import read_bip322_signature_proof

if TYPE_CHECKING:
    from trezor.messages import MultisigRedeemScriptType
    from trezor.enums import InputScriptType
    from apps.common.coininfo import CoinInfo
    from trezor.crypto import bip32
    from apps.common.keychain import Keychain

# This module implements the SLIP-0019 proof of ownership format, see
# https://github.com/satoshilabs/slips/blob/master/slip-0019.md.


_VERSION_MAGIC = b"SL\x00\x19"
_FLAG_USER_CONFIRMED = const(0x01)
_OWNERSHIP_ID_LEN = const(32)
_OWNERSHIP_ID_KEY_PATH = [b"SLIP-0019", b"Ownership identification key"]


def generate_proof(
    node: bip32.HDNode,
    script_type: InputScriptType,
    multisig: MultisigRedeemScriptType | None,
    coin: CoinInfo,
    user_confirmed: bool,
    ownership_ids: list[bytes],
    script_pubkey: bytes,
    commitment_data: bytes,
) -> tuple[bytes, bytes]:
    from trezor.enums import InputScriptType
    from apps.bitcoin.writers import (
        write_bytes_fixed,
        write_compact_size,
        write_uint8,
    )
    from .scripts import write_bip322_signature_proof
    from . import common

    flags = 0
    if user_confirmed:
        flags |= _FLAG_USER_CONFIRMED

    proof = utils.empty_bytearray(4 + 1 + 1 + len(ownership_ids) * _OWNERSHIP_ID_LEN)

    write_bytes_fixed(proof, _VERSION_MAGIC, 4)
    write_uint8(proof, flags)
    write_compact_size(proof, len(ownership_ids))
    for ownership_id in ownership_ids:
        write_bytes_fixed(proof, ownership_id, _OWNERSHIP_ID_LEN)

    sighash = HashWriter(sha256(proof))
    write_bytes_prefixed(sighash, script_pubkey)
    write_bytes_prefixed(sighash, commitment_data)
    if script_type in (
        InputScriptType.SPENDADDRESS,
        InputScriptType.SPENDMULTISIG,
        InputScriptType.SPENDWITNESS,
        InputScriptType.SPENDP2SHWITNESS,
    ):
        signature = common.ecdsa_sign(node, sighash.get_digest())
    elif script_type == InputScriptType.SPENDTAPROOT:
        signature = common.bip340_sign(node, sighash.get_digest())
    else:
        raise DataError("Unsupported script type.")
    public_key = node.public_key()
    write_bip322_signature_proof(
        proof, script_type, multisig, coin, public_key, signature
    )

    return proof, signature


def verify_nonownership(
    proof: bytes,
    script_pubkey: bytes,
    commitment_data: bytes | None,
    keychain: Keychain,
    coin: CoinInfo,
) -> bool:
    from .verification import SignatureVerifier

    try:
        r = utils.BufferReader(proof)
        if r.read_memoryview(4) != _VERSION_MAGIC:
            raise DataError("Unknown format of proof of ownership")

        flags = r.get()
        if flags & 0b1111_1110:
            raise DataError("Unknown flags in proof of ownership")

        # Determine whether our ownership ID appears in the proof.
        id_count = read_compact_size(r)
        ownership_id = get_identifier(script_pubkey, keychain)
        not_owned = True
        for _ in range(id_count):
            if utils.consteq(ownership_id, r.read_memoryview(_OWNERSHIP_ID_LEN)):
                not_owned = False

        # Verify the BIP-322 SignatureProof.

        proof_body = memoryview(proof)[: r.offset]
        if commitment_data is None:
            commitment_data = bytes()

        sighash = HashWriter(sha256(proof_body))
        write_bytes_prefixed(sighash, script_pubkey)
        write_bytes_prefixed(sighash, commitment_data)
        script_sig, witness = read_bip322_signature_proof(r)

        # We don't call verifier.ensure_hash_type() to avoid possible compatibility
        # issues between implementations, because the hash type doesn't influence
        # the digest and the value to use is not defined in BIP-322.
        verifier = SignatureVerifier(script_pubkey, script_sig, witness, coin)
        verifier.verify(sighash.get_digest())
    except (ValueError, EOFError):
        raise DataError("Invalid proof of ownership")

    return not_owned


def read_scriptsig_witness(ownership_proof: bytes) -> tuple[memoryview, memoryview]:
    try:
        r = utils.BufferReader(ownership_proof)
        if r.read_memoryview(4) != _VERSION_MAGIC:
            raise DataError("Unknown format of proof of ownership")

        flags = r.get()
        if flags & 0b1111_1110:
            raise DataError("Unknown flags in proof of ownership")

        # Skip ownership IDs.
        id_count = read_compact_size(r)
        r.read_memoryview(_OWNERSHIP_ID_LEN * id_count)

        return read_bip322_signature_proof(r)

    except (ValueError, EOFError):
        raise DataError("Invalid proof of ownership")


def get_identifier(script_pubkey: bytes, keychain: Keychain) -> bytes:
    from trezor.crypto import hmac

    # k = Key(m/"SLIP-0019"/"Ownership identification key")
    node = keychain.derive_slip21(_OWNERSHIP_ID_KEY_PATH)

    # id = HMAC-SHA256(key = k, msg = scriptPubKey)
    return hmac(hmac.SHA256, node.key(), script_pubkey).digest()
