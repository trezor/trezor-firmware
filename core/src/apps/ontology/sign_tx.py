from trezor import wire
from trezor.crypto.curve import nist256p1
from trezor.crypto.hashlib import sha256
from trezor.messages import OntologyAsset
from trezor.messages.OntologySignedTx import OntologySignedTx
from trezor.messages.OntologySignTx import OntologySignTx
from trezor.utils import HashWriter

from .helpers import CURVE, validate_full_path
from .layout import (
    require_confirm_ont_id_add_attributes,
    require_confirm_ont_id_register,
    require_confirm_transfer_ong,
    require_confirm_transfer_ont,
    require_confirm_withdraw_ong,
)
from .serialize import (
    serialize_ont_id_add_attributes,
    serialize_ont_id_register,
    serialize_transfer,
    serialize_tx,
    serialize_withdraw_ong,
)

from apps.common import paths


async def sign_tx(ctx, msg: OntologySignTx, keychain) -> OntologySignedTx:
    await paths.validate_path(ctx, validate_full_path, keychain, msg.address_n, CURVE)

    if msg.transfer:
        return await sign_transfer(ctx, msg, keychain)
    elif msg.withdraw_ong:
        return await sign_withdraw_ong(ctx, msg, keychain)
    elif msg.ont_id_register:
        return await sign_ont_id_register(ctx, msg, keychain)
    elif msg.ont_id_add_attributes:
        return await sign_ont_id_add_attributes(ctx, msg, keychain)


async def sign(raw_data: bytes, private_key: bytes) -> bytes:
    """
    Creates signature for data
    """
    data_hash = sha256(sha256(raw_data).digest()).digest()

    signature = nist256p1.sign(private_key, data_hash, False)
    signature = b"\x01" + signature[1:65]  # first byte of transaction is 0x01
    return signature


async def sign_transfer(ctx, msg: OntologySignTx, keychain) -> OntologySignedTx:
    if msg.transaction.type == 0xD1:
        if msg.transfer.asset == OntologyAsset.ONT:
            await require_confirm_transfer_ont(
                ctx, msg.transfer.to_address, msg.transfer.amount
            )
        if msg.transfer.asset == OntologyAsset.ONG:
            await require_confirm_transfer_ong(
                ctx, msg.transfer.to_address, msg.transfer.amount
            )
    else:
        raise wire.DataError("Invalid transaction type")

    node = keychain.derive(msg.address_n, CURVE)
    hw = HashWriter(sha256())
    serialized_payload = serialize_transfer(msg.transfer)
    serialize_tx(msg.transaction, serialized_payload, hw)
    signature = await sign(hw.get_digest(), node.private_key())

    return OntologySignedTx(signature=signature, payload=serialized_payload)


async def sign_withdraw_ong(ctx, msg: OntologySignTx, keychain) -> OntologySignedTx:
    if msg.transaction.type == 0xD1:
        await require_confirm_withdraw_ong(ctx, msg.withdraw_ong.amount)
    else:
        raise wire.DataError("Invalid transaction type")

    node = keychain.derive(msg.address_n, CURVE)
    hw = HashWriter(sha256())
    serialized_payload = serialize_withdraw_ong(msg.withdraw_ong)
    serialize_tx(msg.transaction, serialized_payload, hw)
    signature = await sign(hw.get_digest(), node.private_key())

    return OntologySignedTx(signature=signature, payload=serialized_payload)


async def sign_ont_id_register(ctx, msg: OntologySignTx, keychain) -> OntologySignedTx:
    if msg.transaction.type == 0xD1:
        await require_confirm_ont_id_register(
            ctx, msg.ont_id_register.ont_id, msg.ont_id_register.public_key
        )
    else:
        raise wire.DataError("Invalid transaction type")

    node = keychain.derive(msg.address_n, CURVE)
    hw = HashWriter(sha256())
    serialized_payload = serialize_ont_id_register(msg.ont_id_register)
    serialize_tx(msg.transaction, serialized_payload, hw)
    signature = await sign(hw.get_digest(), node.private_key())

    return OntologySignedTx(signature=signature, payload=serialized_payload)


async def sign_ont_id_add_attributes(
    ctx, msg: OntologySignTx, keychain
) -> OntologySignedTx:
    if msg.transaction.type == 0xD1:
        await require_confirm_ont_id_add_attributes(
            ctx,
            msg.ont_id_add_attributes.ont_id,
            msg.ont_id_add_attributes.public_key,
            msg.ont_id_add_attributes.ont_id_attributes,
        )
    else:
        raise wire.DataError("Invalid transaction type")

    node = keychain.derive(msg.address_n, CURVE)
    hw = HashWriter(sha256())
    serialized_payload = serialize_ont_id_add_attributes(msg.ont_id_add_attributes)
    serialize_tx(msg.transaction, serialized_payload, hw)
    signature = await sign(hw.get_digest(), node.private_key())

    return OntologySignedTx(signature=signature, payload=serialized_payload)
