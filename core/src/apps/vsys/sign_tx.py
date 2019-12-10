from trezor import wire
from trezor.crypto import base58
from trezor.messages.VsysSignedTx import VsysSignedTx
from trezor.crypto.curve import curve25519_axolotl, curve25519
from trezor.crypto.curve import ed25519

from apps.common import paths
from apps.common.writers import write_bytes, write_uint8, write_uint16_be, write_uint64_be
from apps.vsys import CURVE, helpers, layout
from apps.vsys.constants import *
from trezor.crypto import random


async def sign_tx(ctx, msg, keychain):
    await paths.validate_path(
        ctx, helpers.validate_full_path, keychain, msg.address_n, CURVE
    )

    node = keychain.derive(msg.address_n, CURVE)
    tx = msg.tx

    if tx.protocol != PROTOCOL:
        raise wire.DataError("Invalid protocol")

    if tx.api > SUPPORT_API_VER:
        raise wire.DataError("Not support to sign this transaction. Please upgrade firmware!")

    if tx.opc != OPC_TX:
        raise wire.DataError("Invalid operation code")

    if not tx.fee:
        raise wire.DataError("Invalid fee")

    if not tx.feeScale:
        raise wire.DataError("Invalid fee scale")

    if not tx.timestamp:
        raise wire.DataError("Invalid timestamp")

    sk = helpers.modify_private_key(node.private_key())
    pk = curve25519.publickey(sk)
    pk_base58 = base58.encode(pk)
    if tx.senderPublicKey != pk_base58:
        raise wire.DataError("Public key mismatch. Please confirm you used correct Trezor device.")

    if tx.transactionType == PAYMENT_TX_TYPE:
        await layout.require_confirm_payment_tx(ctx, tx.recipient, tx.amount)
        to_sign_bytes = encode_payment_tx_to_bytes(tx)
    elif tx.transactionType == LEASE_TX_TYPE:
        await layout.require_confirm_lease_tx(ctx, tx.recipient, tx.amount)
        to_sign_bytes = encode_lease_tx_to_bytes(tx)
    elif tx.transactionType == LEASE_CANCEL_TX_TYPE:
        await layout.require_confirm_cancel_lease_tx(ctx, tx.txId)
        to_sign_bytes = encode_cancel_lease_tx_to_bytes(tx)
    else:
        raise wire.DataError("Transaction type unsupported")

    signature = generate_content_signature(to_sign_bytes, sk)
    signature_base58 = base58.encode(signature)
    return VsysSignedTx(signature=signature_base58, api=SIGN_API_VER, protocol=PROTOCOL, opc=OPC_SIGN)


def encode_payment_tx_to_bytes(tx):
    w = bytearray()
    write_uint8(w, tx.transactionType)
    write_uint64_be(w, helpers.convert_to_nano_sec(tx.timestamp))
    write_uint64_be(w, tx.amount)
    write_uint64_be(w, tx.fee)
    write_uint16_be(w, tx.feeScale)
    write_bytes(w, base58.decode(tx.recipient))
    try:
        attachment_bytes = base58.decode(tx.attachment)
    except Exception:
        attachment_bytes = bytes(tx.attachment, 'utf-8')
    write_uint16_be(w, len(attachment_bytes))
    write_bytes(w, attachment_bytes)
    return w


def encode_lease_tx_to_bytes(tx):
    w = bytearray()
    write_uint8(w, tx.transactionType)
    write_bytes(w, base58.decode(tx.recipient))
    write_uint64_be(w, tx.amount)
    write_uint64_be(w, tx.fee)
    write_uint16_be(w, tx.feeScale)
    write_uint64_be(w, helpers.convert_to_nano_sec(tx.timestamp))
    return w


def encode_cancel_lease_tx_to_bytes(tx):
    w = bytearray()
    write_uint8(w, tx.transactionType)
    write_uint64_be(w, tx.fee)
    write_uint16_be(w, tx.feeScale)
    write_uint64_be(w, helpers.convert_to_nano_sec(tx.timestamp))
    write_bytes(w, base58.decode(tx.txId))
    return w


def generate_content_signature(content: bytes, private_key: bytes) -> bytes:
    random64 = random.bytes(64)
    signature = curve25519_axolotl.curve25519_axolotl_sign(private_key, content, random64)
    return signature


def verify_content_signature(content: bytes, public_key: bytes, signature: bytes) -> bool:
    return curve25519_axolotl.curve25519_axolotl_verify(public_key, content, signature)
