from trezor import wire
from trezor.crypto import base58
from trezor.messages.VsysSignedTx import VsysSignedTx

from apps.common import paths
from apps.common.writers import write_bytes, write_uint8, write_uint16_be, write_uint64_be
from apps.vsys import CURVE, helpers, layout
from apps.vsys.constants import *


async def sign_tx(ctx, msg, keychain):
    await paths.validate_path(
        ctx, helpers.validate_full_path, keychain, msg.address_n, CURVE
    )

    node = keychain.derive(msg.address_n, CURVE)

    if msg.protocol != PROTOCOL:
        raise wire.DataError("Invalid protocol")

    if msg.api > SUPPORT_API_VER:
        raise wire.DataError("Not support to sign this transaction. Please upgrade firmware!")

    if msg.opc != OPC_TX:
        raise wire.DataError("Invalid operation code")

    if not msg.fee:
        raise wire.DataError("Invalid fee")

    if not msg.feeScale:
        raise wire.DataError("Invalid fee scale")

    if not msg.timestamp:
        raise wire.DataError("Invalid timestamp")

    if msg.transactionType == PAYMENT_TX_TYPE:
        await layout.require_confirm_payment_tx(ctx, msg.recipient, msg.amount)
        to_sign_bytes = encode_payment_tx_to_bytes(msg)
    elif msg.transactionType == LEASE_TX_TYPE:
        await layout.require_confirm_lease_tx(ctx, msg.recipient, msg.amount)
        to_sign_bytes = encode_lease_tx_to_bytes(msg)
    elif msg.transactionType == LEASE_CANCEL_TX_TYPE:
        await layout.require_confirm_cancel_lease_tx(ctx, msg.recipient, msg.amount)
        to_sign_bytes = encode_cancel_lease_tx_to_bytes(msg)

    signature = ed25519.sign(node.private_key(), to_sign_bytes)
    signature_base58 = base58.encode(signature)
    return VsysSignedTx(signature=signature_base58, api=SIGN_API_VER)


def encode_payment_tx_to_bytes(msg):
    w = bytearray()
    write_uint8(w, msg.transactionType)
    write_uint64_be(w, msg.timestamp)
    write_uint64_be(w, msg.amount)
    write_uint64_be(w, msg.fee)
    write_uint16_be(w, msg.feeScale)
    write_bytes(w, base58.decode(msg.recipient))
    attachment_bytes = base58.decode(msg.attachment)
    write_uint16_be(w, len(attachment_bytes))
    write_bytes(w, attachment_bytes)
    return w


def encode_lease_tx_to_bytes(msg):
    w = bytearray()
    write_uint8(w, msg.transactionType)
    write_bytes(w, base58.decode(msg.recipient))
    write_uint64_be(w, msg.amount)
    write_uint64_be(w, msg.fee)
    write_uint16_be(w, msg.feeScale)
    write_uint64_be(w, msg.timestamp)
    return w


def encode_cancel_lease_tx_to_bytes(msg):
    w = bytearray()
    write_uint8(w, msg.transactionType)
    write_uint64_be(w, msg.fee)
    write_uint16_be(w, msg.feeScale)
    write_uint64_be(w, msg.timestamp)
    write_bytes(w, base58.decode(msg.txId))
    return w

