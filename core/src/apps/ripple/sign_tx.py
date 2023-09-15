from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain

if TYPE_CHECKING:
    from trezor.messages import RippleSignedTx, RippleSignTx

    from apps.common.keychain import Keychain


# NOTE: it is one big function because that way it is the most flash-space-efficient
@auto_keychain(__name__)
async def sign_tx(msg: RippleSignTx, keychain: Keychain) -> RippleSignedTx:
    from trezor.crypto import der
    from trezor.crypto.curve import secp256k1
    from trezor.crypto.hashlib import sha512
    from trezor.messages import RippleSignedTx
    from trezor.wire import ProcessError

    from apps.common import paths

    from . import helpers, layout
    from .serialize import serialize

    payment = msg.payment  # local_cache_attribute

    if payment.amount > helpers.MAX_ALLOWED_AMOUNT:
        raise ProcessError("Amount exceeds maximum allowed amount.")
    await paths.validate_path(keychain, msg.address_n)

    node = keychain.derive(msg.address_n)
    source_address = helpers.address_from_public_key(node.public_key())

    # Setting canonical flag
    # Our ECDSA implementation already returns fully-canonical signatures,
    # so we're enforcing it in the transaction using the designated flag
    # - see https://wiki.ripple.com/Transaction_Malleability#Using_Fully-Canonical_Signatures
    # - see https://github.com/trezor/trezor-crypto/blob/3e8974ff8871263a70b7fbb9a27a1da5b0d810f7/ecdsa.c#L791
    msg.flags |= helpers.FLAG_FULLY_CANONICAL

    tx = serialize(msg, source_address, node.public_key())
    network_prefix = helpers.HASH_TX_SIGN.to_bytes(4, "big")
    to_sign = network_prefix + tx

    if msg.fee < helpers.MIN_FEE or msg.fee > helpers.MAX_FEE:
        raise ProcessError("Fee must be in the range of 10 to 10,000 drops")

    if payment.destination_tag is not None:
        await layout.require_confirm_destination_tag(payment.destination_tag)
    await layout.require_confirm_tx(
        payment.destination, payment.amount, chunkify=bool(msg.chunkify)
    )
    await layout.require_confirm_total(payment.amount + msg.fee, msg.fee)

    # Signs and encodes signature into DER format
    first_half_of_sha512 = sha512(to_sign).digest()[:32]
    sig = secp256k1.sign(node.private_key(), first_half_of_sha512)
    sig_encoded = der.encode_seq((sig[1:33], sig[33:65]))

    tx = serialize(msg, source_address, node.public_key(), sig_encoded)
    return RippleSignedTx(signature=sig_encoded, serialized_tx=tx)
