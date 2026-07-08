# Quota Manager (QM) counter attestation.
#
# The QM is an external service that owns the authoritative per-wallet global counter.
# It signs that counter with its Ed25519 key; the device verifies the signature against a
# provisioned QM public key before trusting the counter as its anti-rollback ceiling
# (qm_last_counter, set by AuthDbInit). The signed message is
#
#     b"AUTHDB QM v1" || wallet_id || counter(4B BE)
#
# which binds the signature to this specific hidden wallet -- a QM signature for one
# wallet cannot be replayed onto another wallet or device.

# PLACEHOLDER production key (all-zero): production firmware rejects every QM signature
# until a real QM public key is provisioned here.
_QM_PUBKEY = b"\x00" * 32

if __debug__:
    from ubinascii import unhexlify

    # Well-known debug QM public key, accepted only on debug builds. Its 32-byte Ed25519
    # private seed is the ASCII string b"AUTHDB QM DEBUG KEY SEED v1 ....."; tests/tools
    # sign QM counters with it.
    _QM_PUBKEY_DEBUG = unhexlify(
        b"17b4c21f6b55935405d5a48ee3f2f29f42d78c9a650d8f686a705b21ef62b0b6"
    )

_QM_DOMAIN = b"AUTHDB QM v1"


def verify_qm_counter(wallet_id: bytes, counter: int, signature: bytes) -> bool:
    """Verify the QM's Ed25519 signature over (domain || wallet_id || counter)."""
    from trezor.crypto.curve import ed25519

    if len(signature) != 64:
        return False

    message = _QM_DOMAIN + wallet_id + counter.to_bytes(4, "big")
    if ed25519.verify(_QM_PUBKEY, signature, message):
        return True
    if __debug__:
        return ed25519.verify(_QM_PUBKEY_DEBUG, signature, message)
    return False
