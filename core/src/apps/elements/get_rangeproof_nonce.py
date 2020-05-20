from trezor.crypto.curve import secp256k1_zkp
from trezor.crypto.hashlib import sha256
from trezor.messages.ElementsRangeProofNonce import ElementsRangeProofNonce


async def get_rangeproof_nonce(ctx, msg, keychain):
    """Generate shared nonce using ECDH with our SLIP-77 private key and peer's public key."""
    our_privkey = keychain.derive_slip77_blinding_private_key(msg.script_pubkey)
    peer_pubkey = msg.ecdh_pubkey
    context = secp256k1_zkp.Context()
    shared_secret = _compress(context.multiply(our_privkey, peer_pubkey))
    nonce = sha256(sha256(shared_secret).digest()).digest()
    return ElementsRangeProofNonce(nonce=nonce)


def _compress(uncompressed_pubkey: bytes) -> bytes:
    assert len(uncompressed_pubkey) == 65, len(uncompressed_pubkey)
    is_odd = uncompressed_pubkey[-1] & 1
    prefix = b"\x03" if is_odd else b"\x02"
    return prefix + uncompressed_pubkey[1:33]
