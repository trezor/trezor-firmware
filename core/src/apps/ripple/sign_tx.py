from typing import TYPE_CHECKING

from trezor.crypto import der
from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import sha512
from trezor.messages import RippleSignedTx, RippleSignTx
from trezor.wire import ProcessError

from apps.common import paths
from apps.common.keychain import auto_keychain

from . import helpers, layout
from .serialize import serialize

if TYPE_CHECKING:
    from apps.common.keychain import Keychain
    from trezor.wire import Context


@auto_keychain(__name__)
async def sign_tx(
    ctx: Context, msg: RippleSignTx, keychain: Keychain
) -> RippleSignedTx:
    validate(msg)
    await paths.validate_path(ctx, keychain, msg.address_n)

    node = keychain.derive(msg.address_n)
    source_address = helpers.address_from_public_key(node.public_key())

    set_canonical_flag(msg)
    tx = serialize(msg, source_address, pubkey=node.public_key())
    to_sign = get_network_prefix() + tx

    check_fee(msg.fee)
    if msg.payment.destination_tag is not None:
        await layout.require_confirm_destination_tag(ctx, msg.payment.destination_tag)
    await layout.require_confirm_fee(ctx, msg.fee)
    await layout.require_confirm_tx(ctx, msg.payment.destination, msg.payment.amount)

    signature = ecdsa_sign(node.private_key(), first_half_of_sha512(to_sign))
    tx = serialize(msg, source_address, pubkey=node.public_key(), signature=signature)
    return RippleSignedTx(signature=signature, serialized_tx=tx)


def check_fee(fee: int) -> None:
    if fee < helpers.MIN_FEE or fee > helpers.MAX_FEE:
        raise ProcessError("Fee must be in the range of 10 to 10,000 drops")


def get_network_prefix() -> bytes:
    """Network prefix is prepended before the transaction and public key is included"""
    return helpers.HASH_TX_SIGN.to_bytes(4, "big")


def first_half_of_sha512(b: bytes) -> bytes:
    """First half of SHA512, which Ripple uses"""
    hash = sha512(b)
    return hash.digest()[:32]


def ecdsa_sign(private_key: bytes, digest: bytes) -> bytes:
    """Signs and encodes signature into DER format"""
    signature = secp256k1.sign(private_key, digest)
    sig_der = der.encode_seq((signature[1:33], signature[33:65]))
    return sig_der


def set_canonical_flag(msg: RippleSignTx) -> None:
    """
    Our ECDSA implementation already returns fully-canonical signatures,
    so we're enforcing it in the transaction using the designated flag
    - see https://wiki.ripple.com/Transaction_Malleability#Using_Fully-Canonical_Signatures
    - see https://github.com/trezor/trezor-crypto/blob/3e8974ff8871263a70b7fbb9a27a1da5b0d810f7/ecdsa.c#L791
    """
    msg.flags |= helpers.FLAG_FULLY_CANONICAL


def validate(msg: RippleSignTx) -> None:
    if msg.payment.amount > helpers.MAX_ALLOWED_AMOUNT:
        raise ProcessError("Amount exceeds maximum allowed amount.")
