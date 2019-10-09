from trezor.crypto import der
from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import sha512
from trezor.messages.RippleSignedTx import RippleSignedTx
from trezor.messages.RippleSignTx import RippleSignTx
from trezor.wire import ProcessError

import apps.ripple.transaction_fields as tx_field
from apps.common import paths
from apps.ripple import CURVE, helpers, layout
from apps.ripple.serialize import serialize


async def sign_tx(ctx, msg: RippleSignTx, keychain):
    validate(msg)

    multisig = bool(msg.multisig and msg.account)

    await paths.validate_path(
        ctx, helpers.validate_full_path, keychain, msg.address_n, CURVE
    )

    node = keychain.derive(msg.address_n)
    source_address = (
        msg.account if multisig else helpers.address_from_public_key(node.public_key())
    )

    if multisig:
        await layout.require_confirm_multisig(ctx, msg.account)
    check_fee(msg.fee)
    await layout.require_confirm_fee(ctx, msg.fee)

    fields = None

    if msg.payment:
        if msg.payment.destination_tag is not None:
            await layout.require_confirm_destination_tag(
                ctx, msg.payment.destination_tag
            )
        await layout.require_confirm_tx(
            ctx, msg.payment.destination, msg.payment.amount
        )
        fields = tx_field.payment(msg)
    elif msg.signer_list_set:
        await layout.require_confirm_signer_list_set(
            ctx, msg.signer_list_set.signer_quorum, msg.signer_list_set.signer_entries
        )
        fields = tx_field.signer_list_set(msg)
    elif msg.account_set:
        await layout.require_confirm_account_set(ctx, msg.account_set)
        fields = tx_field.account_set(msg)
    else:
        raise ValueError("The message is not supported.")

    set_canonical_flag(msg)
    tx = serialize(msg, fields, multisig, source_address, pubkey=node.public_key())
    to_sign = get_network_prefix(multisig) + tx

    if multisig:
        to_sign += helpers.account_id_from_public_key(node.public_key())

    signature = ecdsa_sign(node.private_key(), first_half_of_sha512(to_sign))
    tx = serialize(
        msg,
        fields,
        multisig,
        source_address,
        pubkey=node.public_key(),
        signature=signature,
    )
    return RippleSignedTx(signature, tx)


def check_fee(fee: int):
    if fee < helpers.MIN_FEE or fee > helpers.MAX_FEE:
        raise ProcessError("Fee must be in the range of 10 to 10,000 drops")


def get_network_prefix(multisig):
    """Network prefix is prepended before the transaction and public key is included"""
    if multisig:
        return helpers.HASH_TX_SIGN_MULTISIG.to_bytes(4, "big")
    else:
        return helpers.HASH_TX_SIGN.to_bytes(4, "big")


def first_half_of_sha512(b):
    """First half of SHA512, which Ripple uses"""
    hash = sha512(b)
    return hash.digest()[:32]


def ecdsa_sign(private_key: bytes, digest: bytes) -> bytes:
    """Signs and encodes signature into DER format"""
    signature = secp256k1.sign(private_key, digest)
    sig_der = der.encode_seq((signature[1:33], signature[33:65]))
    return sig_der


def set_canonical_flag(msg: RippleSignTx):
    """
    Our ECDSA implementation already returns fully-canonical signatures,
    so we're enforcing it in the transaction using the designated flag
    - see https://wiki.ripple.com/Transaction_Malleability#Using_Fully-Canonical_Signatures
    - see https://github.com/trezor/trezor-crypto/blob/3e8974ff8871263a70b7fbb9a27a1da5b0d810f7/ecdsa.c#L791
    """
    if msg.flags is None:
        msg.flags = 0
    msg.flags |= helpers.FLAG_FULLY_CANONICAL


def validate(msg: RippleSignTx):
    if None in (msg.fee, msg.sequence) or (
        msg.payment and None in (msg.payment.amount, msg.payment.destination)
    ):
        raise ProcessError(
            "Some of the required fields are missing (fee, sequence, payment.amount, payment.destination)"
        )
