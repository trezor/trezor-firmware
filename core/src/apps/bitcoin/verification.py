from trezor import utils, wire
from trezor.crypto import der
from trezor.crypto.curve import bip340, secp256k1
from trezor.crypto.hashlib import sha256

from .common import OP_0, OP_1, ecdsa_hash_pubkey
from .scripts import (
    output_script_native_segwit,
    output_script_p2pkh,
    output_script_p2sh,
    parse_input_script_multisig,
    parse_input_script_p2pkh,
    parse_output_script_multisig,
    parse_output_script_p2tr,
    parse_witness_multisig,
    parse_witness_p2tr,
    parse_witness_p2wpkh,
    write_input_script_p2wpkh_in_p2sh,
    write_input_script_p2wsh_in_p2sh,
)

if False:
    from typing import Sequence
    from apps.common.coininfo import CoinInfo


class SignatureVerifier:
    def __init__(
        self,
        script_pubkey: bytes,
        script_sig: bytes | None,
        witness: bytes | None,
        coin: CoinInfo,
    ):
        self.threshold = 1
        self.public_keys: list[memoryview] = []
        self.signatures: list[tuple[memoryview, int]] = []
        self.is_taproot = False

        if not script_sig:
            if not witness:
                raise wire.DataError("Signature data not provided")

            if len(script_pubkey) == 22:  # P2WPKH
                public_key, signature, hash_type = parse_witness_p2wpkh(witness)
                pubkey_hash = ecdsa_hash_pubkey(public_key, coin)
                if output_script_native_segwit(0, pubkey_hash) != script_pubkey:
                    raise wire.DataError("Invalid public key hash")
                self.public_keys = [public_key]
                self.signatures = [(signature, hash_type)]
            elif len(script_pubkey) == 34 and script_pubkey[0] == OP_0:  # P2WSH
                script, self.signatures = parse_witness_multisig(witness)
                script_hash = sha256(script).digest()
                if output_script_native_segwit(0, script_hash) != script_pubkey:
                    raise wire.DataError("Invalid script hash")
                self.public_keys, self.threshold = parse_output_script_multisig(script)
            elif len(script_pubkey) == 34 and script_pubkey[0] == OP_1:  # P2TR
                self.is_taproot = True
                self.public_keys = [parse_output_script_p2tr(script_pubkey)]
                self.signatures = [parse_witness_p2tr(witness)]
            else:
                raise wire.DataError("Unsupported signature script")
        elif witness and witness != b"\x00":
            if len(script_sig) == 23:  # P2WPKH nested in BIP16 P2SH
                public_key, signature, hash_type = parse_witness_p2wpkh(witness)
                pubkey_hash = ecdsa_hash_pubkey(public_key, coin)
                w = utils.empty_bytearray(23)
                write_input_script_p2wpkh_in_p2sh(w, pubkey_hash)
                if w != script_sig:
                    raise wire.DataError("Invalid public key hash")
                script_hash = coin.script_hash(script_sig[1:]).digest()
                if output_script_p2sh(script_hash) != script_pubkey:
                    raise wire.DataError("Invalid script hash")
                self.public_keys = [public_key]
                self.signatures = [(signature, hash_type)]
            elif len(script_sig) == 35:  # P2WSH nested in BIP16 P2SH
                script, self.signatures = parse_witness_multisig(witness)
                script_hash = sha256(script).digest()
                w = utils.empty_bytearray(35)
                write_input_script_p2wsh_in_p2sh(w, script_hash)
                if w != script_sig:
                    raise wire.DataError("Invalid script hash")
                script_hash = coin.script_hash(script_sig[1:]).digest()
                if output_script_p2sh(script_hash) != script_pubkey:
                    raise wire.DataError("Invalid script hash")
                self.public_keys, self.threshold = parse_output_script_multisig(script)
            else:
                raise wire.DataError("Unsupported signature script")
        else:
            if len(script_pubkey) == 25:  # P2PKH
                public_key, signature, hash_type = parse_input_script_p2pkh(script_sig)
                pubkey_hash = ecdsa_hash_pubkey(public_key, coin)
                if output_script_p2pkh(pubkey_hash) != script_pubkey:
                    raise wire.DataError("Invalid public key hash")
                self.public_keys = [public_key]
                self.signatures = [(signature, hash_type)]
            elif len(script_pubkey) == 23:  # P2SH
                script, self.signatures = parse_input_script_multisig(script_sig)
                script_hash = coin.script_hash(script).digest()
                if output_script_p2sh(script_hash) != script_pubkey:
                    raise wire.DataError("Invalid script hash")
                self.public_keys, self.threshold = parse_output_script_multisig(script)
            else:
                raise wire.DataError("Unsupported signature script")

        if self.threshold != len(self.signatures):
            raise wire.DataError("Invalid signature")

    def ensure_hash_type(self, hash_types: Sequence[int]) -> None:
        if any(h not in hash_types for _, h in self.signatures):
            raise wire.DataError("Unsupported sighash type")

    def verify(self, digest: bytes) -> None:
        # It is up to the caller to ensure that the digest is appropriate for
        # the hash type used by the signatures. If a signature is using a
        # different hash type than expected, then verification will fail. To
        # return the proper error message, the caller can optionally check the
        # hash type by using ensure_hash_type() before calling verify.

        if self.is_taproot:
            self.verify_bip340(digest)
        else:
            self.verify_ecdsa(digest)

    def verify_bip340(self, digest: bytes) -> None:
        if not bip340.verify(self.public_keys[0], self.signatures[0][0], digest):
            raise wire.DataError("Invalid signature")

    def verify_ecdsa(self, digest: bytes) -> None:
        try:
            i = 0
            for der_signature, _ in self.signatures:
                signature = decode_der_signature(der_signature)
                while not secp256k1.verify(self.public_keys[i], signature, digest):
                    i += 1
        except Exception:
            raise wire.DataError("Invalid signature")


def decode_der_signature(der_signature: memoryview) -> bytearray:
    seq = der.decode_seq(der_signature)
    if len(seq) != 2 or any(len(i) > 32 for i in seq):
        raise ValueError

    signature = bytearray(64)
    signature[32 - len(seq[0]) : 32] = seq[0]
    signature[64 - len(seq[1]) : 64] = seq[1]

    return signature
