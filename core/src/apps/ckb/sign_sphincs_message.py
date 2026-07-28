"""Sign a message with a CKB SPHINCS+ post-quantum key.

Mirrors the ECDSA CKB message flow (blake2b "Nervos Message:" digest, on-device
confirmation) but signs with FIPS 205 SLH-DSA. The signature reaches ~50 KB and
exceeds the THP buffer, so it is streamed back in chunks via TXSIGCHUNK,
terminated by CKBSphincsPlusMessageSignature.
"""

from typing import TYPE_CHECKING

from trezor.wire import DataError

from . import helpers
from .get_sphincs_address import (
    _MAX_ACCOUNT_INDEX,
    _VALID_VARIANTS,
    _address_from_pubkey,
    _require_sphincs_mnemonic,
    _wipe,
)

if TYPE_CHECKING:
    from trezor.messages import CKBSphincsPlusMessageSignature, CKBSphincsPlusSignMessage

# Chunk size for streaming the signature, well under the THP buffer (~8 KB).
_SIG_CHUNK_SIZE = 4096


def _fips205_message(message: bytes) -> bytes:
    """Domain-wrap a text message for SPHINCS+ signing.

    digest = blake2b("ckb-default-hash", "Nervos Message:" || message), then the
    two-byte FIPS 205 pure-signing prefix (prehash=0, empty context) — the same
    wrapping sign_sphincs_tx applies to ckb_tx_message_all. The "Nervos Message:"
    personalization keeps a text signature from ever colliding with a tx
    signature (which uses the "ckb-sphincs+-msg" personal instead).
    """
    return b"\x00\x00" + helpers.message_digest(message)


async def sign_sphincs_message(
    msg: "CKBSphincsPlusSignMessage",
) -> "CKBSphincsPlusMessageSignature":
    from trezor.crypto import sphincsplus
    from trezor.enums import CKBTxRequestType
    from trezor.messages import (
        CKBSphincsPlusMessageSignature,
        CKBTxAckSigChunk,
        CKBTxRequest,
        CKBTxRequestDetails,
        CKBTxRequestSerialized,
    )
    from trezor.ui.layouts import confirm_signverify
    from trezor.wire.context import call

    from apps.common.signverify import decode_message

    variant = msg.variant if msg.variant is not None else 49
    if variant not in _VALID_VARIANTS:
        raise DataError("Invalid SPHINCS+ variant")
    if msg.network not in ("Mainnet", "Testnet"):
        raise DataError("Invalid CKB network")
    account_index = msg.account_index if msg.account_index is not None else 0
    if account_index < 0 or account_index > _MAX_ACCOUNT_INDEX:
        raise DataError("Invalid SPHINCS+ account index")

    # The confirmation below raises ActionCancelled, which must reach _wipe.
    seed = _require_sphincs_mnemonic(variant)
    try:
        public_key = sphincsplus.derive_public_key(seed, account_index, variant)
        address = _address_from_pubkey(public_key, variant, msg.network)

        await confirm_signverify(
            decode_message(msg.message),
            address,
            verify=False,
            account="CKB SPHINCS+",
            path="QP/{}/v{}".format(account_index, variant),
            chunkify=bool(msg.chunkify),
        )

        signed_pk, signature = sphincsplus.derive_and_sign(
            seed, account_index, variant, _fips205_message(msg.message)
        )
        if signed_pk != public_key:
            raise DataError("SPHINCS+ public key mismatch (possible fault injection)")
    finally:
        _wipe(seed)

    total = len(signature)
    offset = 0
    while offset < total:
        chunk = signature[offset : offset + _SIG_CHUNK_SIZE]
        await call(
            CKBTxRequest(
                request_type=CKBTxRequestType.TXSIGCHUNK,
                details=CKBTxRequestDetails(
                    signature_offset=offset, signature_total_size=total
                ),
                serialized=CKBTxRequestSerialized(signature=chunk),
            ),
            CKBTxAckSigChunk,
        )
        offset += len(chunk)

    return CKBSphincsPlusMessageSignature(
        address=address,
        public_key=public_key,
        variant=variant,
    )
