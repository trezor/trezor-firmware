from trezor.crypto import der
from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import sha512
from trezor.messages.RippleAccountDelete import RippleAccountDelete
from trezor.messages.RippleAccountSet import RippleAccountSet
from trezor.messages.RippleCheckCancel import RippleCheckCancel
from trezor.messages.RippleCheckCash import RippleCheckCash
from trezor.messages.RippleCheckCreate import RippleCheckCreate
from trezor.messages.RippleDepositPreauth import RippleDepositPreauth
from trezor.messages.RippleEscrowCancel import RippleEscrowCancel
from trezor.messages.RippleEscrowCreate import RippleEscrowCreate
from trezor.messages.RippleEscrowFinish import RippleEscrowFinish
from trezor.messages.RippleInternalSigner import RippleInternalSigner
from trezor.messages.RippleOfferCancel import RippleOfferCancel
from trezor.messages.RippleOfferCreate import RippleOfferCreate
from trezor.messages.RipplePayment import RipplePayment
from trezor.messages.RipplePaymentChannelClaim import RipplePaymentChannelClaim
from trezor.messages.RipplePaymentChannelCreate import RipplePaymentChannelCreate
from trezor.messages.RipplePaymentChannelFund import RipplePaymentChannelFund
from trezor.messages.RippleSetRegularKey import RippleSetRegularKey
from trezor.messages.RippleSignedTx import RippleSignedTx
from trezor.messages.RippleSigner import RippleSigner
from trezor.messages.RippleSignerListSet import RippleSignerListSet
from trezor.messages.RippleSignTx import RippleSignTx
from trezor.messages.RippleTrustSet import RippleTrustSet
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
        validate(msg, transaction_type)

        await layout.require_confirm_payment(
            ctx,
            msg.flags,
            msg.payment.amount,
            msg.payment.destination,
            msg.payment.issued_amount,
            msg.payment.destination_tag,
            msg.payment.paths,
            msg.payment.invoice_id,
            msg.payment.send_max,
            msg.payment.issued_send_max,
            msg.payment.deliver_min,
            msg.payment.issued_deliver_min,
        )
    elif isinstance(msg.set_regular_key, RippleSetRegularKey):
        transaction_type = "set_regular_key"
        validate(msg, transaction_type)

        await layout.require_confirm_regular_key(ctx, msg.set_regular_key.regular_key)
    elif isinstance(msg.escrow_create, RippleEscrowCreate):
        transaction_type = "escrow_create"
        validate(msg, transaction_type)

        await layout.require_confirm_escrow_create(
            ctx,
            msg.escrow_create.amount,
            msg.escrow_create.destination,
            msg.escrow_create.cancel_after,
            msg.escrow_create.finish_after,
            msg.escrow_create.condition,
            msg.escrow_create.destination_tag,
        )
    elif isinstance(msg.escrow_cancel, RippleEscrowCancel):
        transaction_type = "escrow_cancel"
        validate(msg, transaction_type)

        await layout.require_confirm_escrow_cancel(
            ctx, msg.escrow_cancel.owner, msg.escrow_cancel.offer_sequence
        )
    elif isinstance(msg.escrow_finish, RippleEscrowFinish):
        transaction_type = "escrow_finish"
        validate(msg, transaction_type)

        await layout.require_confirm_escrow_finish(
            ctx,
            msg.escrow_finish.owner,
            msg.escrow_finish.offer_sequence,
            msg.escrow_finish.condition,
            msg.escrow_finish.fulfillment,
        )
    elif isinstance(msg.account_set, RippleAccountSet):
        transaction_type = "account_set"
        validate(msg, transaction_type)
        if (
            msg.account_set.transfer_rate is not None
            and msg.account_set.transfer_rate < 1000000000
            and msg.account_set.transfer_rate != 0
        ):
            raise ProcessError("Invalid transfer rate")

        await layout.require_confirm_account_set(
            ctx,
            msg.flags,
            msg.account_set.clear_flag,
            msg.account_set.set_flag,
            msg.account_set.domain,
            msg.account_set.email_hash,
            msg.account_set.message_key,
            msg.account_set.transfer_rate,
            msg.account_set.tick_size,
        )
    elif isinstance(msg.payment_channel_create, RipplePaymentChannelCreate):
        transaction_type = "payment_channel_create"
        validate(msg, transaction_type)

        await layout.require_confirm_payment_channel_create(
            ctx,
            msg.payment_channel_create.amount,
            msg.payment_channel_create.destination,
            msg.payment_channel_create.settle_delay,
            msg.payment_channel_create.public_key,
            msg.payment_channel_create.cancel_after,
            msg.payment_channel_create.destination_tag,
        )
    elif isinstance(msg.payment_channel_fund, RipplePaymentChannelFund):
        transaction_type = "payment_channel_fund"
        validate(msg, transaction_type)

        await layout.require_confirm_payment_channel_fund(
            ctx,
            msg.payment_channel_fund.amount,
            msg.payment_channel_fund.channel,
            msg.payment_channel_fund.expiration,
        )
    elif isinstance(msg.payment_channel_claim, RipplePaymentChannelClaim):
        transaction_type = "payment_channel_claim"
        validate(msg, transaction_type)

        await layout.require_confirm_payment_channel_claim(
            ctx,
            msg.flags,
            msg.payment_channel_claim.channel,
            msg.payment_channel_claim.balance,
            msg.payment_channel_claim.amount,
            msg.payment_channel_claim.signature,
            msg.payment_channel_claim.public_key,
        )
    elif isinstance(msg.trust_set, RippleTrustSet):
        transaction_type = "trust_set"
        validate(msg, transaction_type)

        await layout.require_confirm_trust_set(
            ctx,
            msg.flags,
            msg.trust_set.limit_amount,
            msg.trust_set.quality_in,
            msg.trust_set.quality_out,
        )
    elif isinstance(msg.offer_create, RippleOfferCreate):
        transaction_type = "offer_create"
        validate(msg, transaction_type)

        await layout.require_confirm_offer_create(
            ctx,
            msg.flags,
            msg.offer_create.expiration,
            msg.offer_create.offer_sequence,
            msg.offer_create.taker_gets,
            msg.offer_create.issued_taker_gets,
            msg.offer_create.taker_pays,
            msg.offer_create.issued_taker_pays,
        )
    elif isinstance(msg.offer_cancel, RippleOfferCancel):
        transaction_type = "offer_cancel"
        validate(msg, transaction_type)

        await layout.require_confirm_offer_cancel(ctx, msg.offer_cancel.offer_sequence)
    elif isinstance(msg.signer_list_set, RippleSignerListSet):
        transaction_type = "signer_list_set"
        validate(msg, transaction_type)

        await layout.require_confirm_signer_list_set(
            ctx, msg.signer_list_set.signer_quorum, msg.signer_list_set.signer_entries
        )
    elif isinstance(msg.check_create, RippleCheckCreate):
        transaction_type = "check_create"
        validate(msg, transaction_type)

        await layout.require_confirm_check_create(
            ctx,
            msg.check_create.destination,
            msg.check_create.send_max,
            msg.check_create.issued_send_max,
            msg.check_create.destination_tag,
            msg.check_create.expiration,
            msg.check_create.invoice_id,
        )
    elif isinstance(msg.check_cancel, RippleCheckCancel):
        transaction_type = "check_cancel"
        validate(msg, transaction_type)

        await layout.require_confirm_check_cancel(ctx, msg.check_cancel.check_id)
    elif isinstance(msg.check_cash, RippleCheckCash):
        transaction_type = "check_cash"
        validate(msg, transaction_type)

        await layout.require_confirm_check_cash(
            ctx,
            msg.check_cash.check_id,
            msg.check_cash.amount,
            msg.check_cash.issued_amount,
            msg.check_cash.deliver_min,
            msg.check_cash.issued_deliver_min,
        )
    elif isinstance(msg.deposit_preauth, RippleDepositPreauth):
        transaction_type = "deposit_preauth"
        validate(msg, transaction_type)

        await layout.require_confirm_deposit_preauth(
            ctx, msg.deposit_preauth.authorize, msg.deposit_preauth.unauthorize
        )
    elif isinstance(msg.account_delete, RippleAccountDelete):
        transaction_type = "account_delete"
        validate(msg, transaction_type)

        await layout.require_confirm_account_delete(
            ctx, msg.account_delete.destination, msg.account_delete.destination_tag
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


def validate(msg: RippleSignTx, transaction_type: str):
    """Checks if the transaction contains all the required fields"""
    if hasattr(msg, transaction_type) and getattr(msg, transaction_type) is not None:
        check_fields(
            getattr(msg, transaction_type),
            definitions.REQUIRED_FIELDS[transaction_type],
        )
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
