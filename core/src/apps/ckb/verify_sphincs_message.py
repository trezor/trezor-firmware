"""Verify a CKB SPHINCS+ post-quantum message signature on the device.

The signature is keyless to verify (it uses the host-supplied public key), so no
mnemonic is touched. Because SPHINCS+ signatures exceed the THP buffer, the host
streams the signature in: the device drives the transfer with CKBTxRequest{
TXSIGCHUNK} and the host answers each chunk in CKBTxAckSigChunk.signature.
"""

from typing import TYPE_CHECKING

from trezor.wire import DataError

from .get_sphincs_address import _VALID_VARIANTS, _address_from_pubkey
from .sign_sphincs_message import _fips205_message

if TYPE_CHECKING:
    from trezor.messages import CKBSphincsPlusVerifyMessage, Success

# Largest SPHINCS+ signature is ~49856 bytes (256f); cap the incoming stream a
# little above that to bound memory and reject malformed totals.
_MAX_SIGNATURE_SIZE = 51000


async def verify_sphincs_message(msg: "CKBSphincsPlusVerifyMessage") -> "Success":
    from trezor import TR
    from trezor.crypto import sphincsplus
    from trezor.enums import CKBTxRequestType
    from trezor.messages import (
        CKBTxAckSigChunk,
        CKBTxRequest,
        CKBTxRequestDetails,
        Success,
    )
    from trezor.ui.layouts import confirm_signverify, show_success
    from trezor.wire import ProcessError
    from trezor.wire.context import call

    from apps.common.signverify import decode_message

    variant = msg.variant
    if variant not in _VALID_VARIANTS:
        raise DataError("Invalid SPHINCS+ variant")
    if msg.network not in ("Mainnet", "Testnet"):
        raise DataError("Invalid CKB network")

    # Bind the public key to the claimed address: a valid signature is only
    # meaningful for the address derived from that key.
    if _address_from_pubkey(msg.public_key, variant, msg.network) != msg.address:
        raise ProcessError("Public key does not match address")

    total = msg.signature_total_size
    if total == 0 or total > _MAX_SIGNATURE_SIZE:
        raise DataError("Invalid signature size")

    # Stream the signature in from the host (device requests each chunk by
    # offset, host returns it in CKBTxAckSigChunk.signature).
    signature = bytearray()
    while len(signature) < total:
        ack = await call(
            CKBTxRequest(
                request_type=CKBTxRequestType.TXSIGCHUNK,
                details=CKBTxRequestDetails(
                    signature_offset=len(signature), signature_total_size=total
                ),
            ),
            CKBTxAckSigChunk,
        )
        chunk = bytes(ack.signature) if ack.signature else b""
        if not chunk:
            raise DataError("Empty signature chunk")
        signature.extend(chunk)
        if len(signature) > total:
            raise DataError("Signature exceeds declared size")

    if not sphincsplus.verify(
        msg.public_key, bytes(signature), _fips205_message(msg.message), variant
    ):
        raise ProcessError("Invalid signature")

    await confirm_signverify(
        decode_message(msg.message),
        msg.address,
        verify=True,
        chunkify=bool(msg.chunkify),
    )
    await show_success("verify_message", TR.bitcoin__valid_signature)
    return Success(message="Message verified")
