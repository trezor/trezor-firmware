from micropython import const

# WARD Manager (WM/QM) Ed25519 state attestations.
#
# The WM owns the authoritative per-wallet (counter, mac). The device verifies its
# signatures against a provisioned WM public key before trusting the attested state.
# Two attestation preimages are used:
#   - freshness/ingest (WARDIngestAttestation):
#       b"WARD ATTEST v1" || version(1B) || nonce || wallet_id || counter(4B BE) || mac
#     the nonce (minted at WARDInitSyncRound) makes it anti-replay per round.
#   - final/commit (WARDConfirmCommit):
#       b"WARD FINAL v1" || wallet_id || counter(4B BE) || mac
# Both bind the signature to this specific hidden wallet.

# PLACEHOLDER production key (all-zero): production firmware rejects every WM signature
# until a real WM public key is provisioned here.
_QM_PUBKEY = b"\x00" * 32

if __debug__:
    from ubinascii import unhexlify

    # Well-known debug WM public key, accepted only on debug builds. Its 32-byte Ed25519
    # private seed is the ASCII string b"AUTHDB QM DEBUG KEY SEED v1 ...."; tests/tools
    # sign attestations with it.
    _QM_PUBKEY_DEBUG = unhexlify(
        b"17b4c21f6b55935405d5a48ee3f2f29f42d78c9a650d8f686a705b21ef62b0b6"
    )

# WARDIngestAttestation freshness attestation.
_WARD_ATTEST_DOMAIN = b"WARD ATTEST v1"
_WARD_ATTEST_VERSION = const(1)
# WARDConfirmCommit attestation: the WM signs the exact committed candidate.
_WARD_FINAL_DOMAIN = b"WARD FINAL v1"


def _verify(message: bytes, signature: bytes) -> bool:
    from trezor.crypto.curve import ed25519

    if len(signature) != 64:
        return False
    if ed25519.verify(_QM_PUBKEY, signature, message):
        return True
    if __debug__:
        return ed25519.verify(_QM_PUBKEY_DEBUG, signature, message)
    return False


def verify_wm_attestation(
    wallet_id: bytes, nonce: bytes, counter: int, mac: bytes, signature: bytes
) -> bool:
    """Verify the WM's freshness attestation for a sync round:

        b"WARD ATTEST v1" || version(1B) || nonce || wallet_id || counter(4B BE) || mac

    `nonce` is the per-round value minted at WARDInitSyncRound (anti-replay); `mac`
    is the attested root MAC (all-zero for an empty tree).
    """
    message = (
        _WARD_ATTEST_DOMAIN
        + bytes([_WARD_ATTEST_VERSION])
        + nonce
        + wallet_id
        + counter.to_bytes(4, "big")
        + mac
    )
    return _verify(message, signature)


def verify_ward_final(
    wallet_id: bytes, counter: int, mac: bytes, signature: bytes
) -> bool:
    """Verify the WM's final attestation over the committed WARD candidate:

        b"WARD FINAL v1" || wallet_id || counter(4B BE) || mac

    `mac` is the candidate root MAC (all-zero for a candidate that empties the
    tree). The signature binds the WM to the exact (counter, mac) the device
    produced, so WARDConfirmCommit can safely advance the counter.
    """
    message = _WARD_FINAL_DOMAIN + wallet_id + counter.to_bytes(4, "big") + mac
    return _verify(message, signature)
