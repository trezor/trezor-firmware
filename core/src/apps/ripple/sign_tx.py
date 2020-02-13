from trezor.crypto import der
from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import sha512
from trezor.messages.RippleInternalSigner import RippleInternalSigner
from trezor.messages.RipplePayment import RipplePayment
from trezor.messages.RippleSignedTx import RippleSignedTx
from trezor.messages.RippleSigner import RippleSigner
from trezor.messages.RippleSignTx import RippleSignTx
from trezor.wire import ProcessError

from apps.common import paths
from apps.ripple import CURVE, definitions, helpers, layout
from apps.ripple.serialize import serialize


async def sign_tx(ctx, msg: RippleSignTx, keychain):
    await paths.validate_path(
        ctx, helpers.validate_full_path, keychain, msg.address_n, CURVE
    )
    set_canonical_flag(msg)

    node = keychain.derive(msg.address_n)
    if not msg.account:
        msg.account = helpers.address_from_public_key(node.public_key())

    multi_sign = False
    if msg.signing_pub_key == "":
        multi_sign = True
    elif msg.signing_pub_key is None:
        msg.signing_pub_key = helpers.bytes_to_hex(node.public_key())
    else:
        own_pub_key = helpers.bytes_to_hex(node.public_key())
        if own_pub_key.lower() != msg.signing_pub_key.lower():
            raise ProcessError(
                "The supplied SigningPubKey does not match the device public key"
            )

    check_fields(msg, definitions.REQUIRED_FIELDS["common"])
    await layout.require_confirm_common(
        ctx,
        msg.account,
        msg.fee,
        msg.account_txn_id,
        msg.memos,
        msg.signers,
        msg.source_tag,
    )
    if isinstance(msg.payment, RipplePayment):
        transaction_type = "payment"
        validate(msg, transaction_type, legacy=True)

        await layout.require_confirm_payment(
            ctx,
            msg.flags,
            msg.payment.amount,
            msg.payment.destination,
            None,
            msg.payment.destination_tag,
            None,
            None,
            None,
            None,
            None,
            None,
        )
    elif msg.transaction_type == "Payment":
        transaction_type = "payment"
        validate(msg, transaction_type)

        await layout.require_confirm_payment(
            ctx,
            msg.flags,
            msg.amount,
            msg.destination,
            msg.issued_amount,
            msg.destination_tag,
            msg.paths,
            msg.invoice_id,
            msg.send_max,
            msg.issued_send_max,
            msg.deliver_min,
            msg.issued_deliver_min,
        )
    elif msg.transaction_type == "SetRegularKey":
        transaction_type = "set_regular_key"
        validate(msg, transaction_type)

        await layout.require_confirm_regular_key(ctx, msg.regular_key)
    elif msg.transaction_type == "EscrowCreate":
        transaction_type = "escrow_create"
        validate(msg, transaction_type)

        await layout.require_confirm_escrow_create(
            ctx,
            msg.amount,
            msg.destination,
            msg.cancel_after,
            msg.finish_after,
            msg.condition,
            msg.destination_tag,
        )
    elif msg.transaction_type == "EscrowCancel":
        transaction_type = "escrow_cancel"
        validate(msg, transaction_type)

        await layout.require_confirm_escrow_cancel(ctx, msg.owner, msg.offer_sequence)
    elif msg.transaction_type == "EscrowFinish":
        transaction_type = "escrow_finish"
        validate(msg, transaction_type)

        await layout.require_confirm_escrow_finish(
            ctx, msg.owner, msg.offer_sequence, msg.condition, msg.fulfillment
        )
    elif msg.transaction_type == "AccountSet":
        transaction_type = "account_set"
        validate(msg, transaction_type)
        if (
            msg.transfer_rate is not None
            and msg.transfer_rate < 1000000000
            and msg.transfer_rate != 0
        ):
            raise ProcessError("Invalid transfer rate")

        await layout.require_confirm_account_set(
            ctx,
            msg.flags,
            msg.clear_flag,
            msg.set_flag,
            msg.domain,
            msg.email_hash,
            msg.message_key,
            msg.transfer_rate,
            msg.tick_size,
        )
    elif msg.transaction_type == "PaymentChannelCreate":
        transaction_type = "payment_channel_create"
        validate(msg, transaction_type)

        await layout.require_confirm_payment_channel_create(
            ctx,
            msg.amount,
            msg.destination,
            msg.settle_delay,
            msg.public_key,
            msg.cancel_after,
            msg.destination_tag,
        )
    elif msg.transaction_type == "PaymentChannelFund":
        transaction_type = "payment_channel_fund"
        validate(msg, transaction_type)

        await layout.require_confirm_payment_channel_fund(
            ctx, msg.amount, msg.channel, msg.expiration
        )
    elif msg.transaction_type == "PaymentChannelClaim":
        transaction_type = "payment_channel_claim"
        validate(msg, transaction_type)

        await layout.require_confirm_payment_channel_claim(
            ctx,
            msg.flags,
            msg.channel,
            msg.balance,
            msg.amount,
            msg.signature,
            msg.public_key,
        )
    elif msg.transaction_type == "TrustSet":
        transaction_type = "trust_set"
        validate(msg, transaction_type)

        await layout.require_confirm_trust_set(
            ctx, msg.flags, msg.limit_amount, msg.quality_in, msg.quality_out
        )
    elif msg.transaction_type == "OfferCreate":
        transaction_type = "offer_create"
        validate(msg, transaction_type)

        await layout.require_confirm_offer_create(
            ctx,
            msg.flags,
            msg.expiration,
            msg.offer_sequence,
            msg.taker_gets,
            msg.issued_taker_gets,
            msg.taker_pays,
            msg.issued_taker_pays,
        )
    elif msg.transaction_type == "OfferCancel":
        transaction_type = "offer_cancel"
        validate(msg, transaction_type)

        await layout.require_confirm_offer_cancel(ctx, msg.offer_sequence)
    elif msg.transaction_type == "SignerListSet":
        transaction_type = "signer_list_set"
        validate(msg, transaction_type)

        await layout.require_confirm_signer_list_set(
            ctx, msg.signer_quorum, msg.signer_entries
        )
    elif msg.transaction_type == "CheckCreate":
        transaction_type = "check_create"
        validate(msg, transaction_type)

        await layout.require_confirm_check_create(
            ctx,
            msg.destination,
            msg.send_max,
            msg.issued_send_max,
            msg.destination_tag,
            msg.expiration,
            msg.invoice_id,
        )
    elif msg.transaction_type == "CheckCancel":
        transaction_type = "check_cancel"
        validate(msg, transaction_type)

        await layout.require_confirm_check_cancel(ctx, msg.check_id)
    elif msg.transaction_type == "CheckCash":
        transaction_type = "check_cash"
        validate(msg, transaction_type)

        await layout.require_confirm_check_cash(
            ctx,
            msg.check_id,
            msg.amount,
            msg.issued_amount,
            msg.deliver_min,
            msg.issued_deliver_min,
        )
    elif msg.transaction_type == "DepositPreauth":
        transaction_type = "deposit_preauth"
        validate(msg, transaction_type)

        await layout.require_confirm_deposit_preauth(
            ctx, msg.authorize, msg.unauthorize
        )
    elif msg.transaction_type == "AccountDelete":
        transaction_type = "account_delete"
        validate(msg, transaction_type)

        await layout.require_confirm_account_delete(
            ctx, msg.destination, msg.destination_tag
        )
    else:
        raise ProcessError("Unsupported transaction")
    tx = serialize(msg, for_signing=True, transaction_type=transaction_type)
    to_sign = get_network_prefix(multi_sign) + tx
    if multi_sign:
        to_sign += helpers.account_id_from_public_key(node.public_key())

    signature = ecdsa_sign(node.private_key(), first_half_of_sha512(to_sign))

    if multi_sign:
        msg.signers = add_signer(
            msg.signers,
            account=helpers.address_from_public_key(node.public_key()),
            txn_signature=helpers.bytes_to_hex(signature),
            signing_pub_key=helpers.bytes_to_hex(node.public_key()),
        )

    tx = serialize(
        msg, for_signing=False, signature=signature, transaction_type=transaction_type
    )

    return RippleSignedTx(signature, tx)


def add_signer(signers, account, txn_signature, signing_pub_key):
    if not signers:
        # This is a multi-sign transaction with no previous signers
        signers = [
            RippleSigner(RippleInternalSigner(account, txn_signature, signing_pub_key))
        ]
    else:
        # There are already signers
        signers.append(
            RippleSigner(RippleInternalSigner(account, txn_signature, signing_pub_key))
        )
    # Sort by numerical value of address (https://xrpl.org/multi-signing.html#sending-multi-signed-transactions)
    signers.sort(
        key=lambda signer: int.from_bytes(
            helpers.decode_address(signer.signer.account), "big"
        )
    )
    return signers


def get_network_prefix(multi_sign):
    """Network prefix is prepended before the transaction and public key is included"""
    if multi_sign:
        return definitions.HASH_TX_SIGN_MULTI.to_bytes(4, "big")
    else:
        return definitions.HASH_TX_SIGN.to_bytes(4, "big")


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
    msg.flags |= definitions.FLAG_FULLY_CANONICAL


def validate(msg: RippleSignTx, transaction_type: str, legacy: bool = False):
    """Checks if the transaction contains all the required fields"""
    if (
        legacy
        and hasattr(msg, transaction_type)
        and getattr(msg, transaction_type) is not None
    ):
        check_fields(
            getattr(msg, transaction_type),
            definitions.REQUIRED_FIELDS[transaction_type],
        )
    elif not legacy:
        check_fields(msg, definitions.REQUIRED_FIELDS[transaction_type])
    else:
        raise ProcessError("Transaction field is missing {}".format(transaction_type))


def check_fields(msg, fields):
    """
    Checks for the existence of fields in the message.
    :param fields: List of required fields in `msg`, if one of multiple is required, provide as inner list
    """
    for field in fields:
        has_field = False
        if isinstance(field, list):
            for alternative in field:
                if hasattr(msg, alternative) and getattr(msg, alternative) is not None:
                    has_field = True
                    break
        else:
            if hasattr(msg, field) and getattr(msg, field) is not None:
                has_field = True
        if not has_field:
            raise ProcessError(
                "Some of the following fields are missing {}".format(fields)
            )
