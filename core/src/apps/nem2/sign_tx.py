from trezor.crypto.curve import ed25519
from trezor.crypto.hashlib import sha3_256
from trezor.messages.NEM2SignedTx import NEM2SignedTx
from trezor.messages.NEM2CosignatureSignedTx import NEM2CosignatureSignedTx
from trezor.messages.NEM2SignTx import NEM2SignTx
from ubinascii import unhexlify, hexlify

from apps.common import seed
from apps.common.paths import validate_path
from apps.nem2 import (
    CURVE,
    transfer,
    mosaic,
    namespace,
    metadata,
    aggregate,
    hash_lock,
    secret_lock,
    multisig,
    account_restriction
)
from apps.nem2.helpers import (
    validate_nem2_path,
    NEM2_HASH_ALG,
    NEM2_TRANSACTION_TYPE_AGGREGATE_COMPLETE,
    NEM2_TRANSACTION_TYPE_AGGREGATE_BONDED
)
from apps.nem2.validators import validate

# Included fields are `size`, `verifiableEntityHeader_Reserved1`,
# `signature`, `signerPublicKey` and `entityBody_Reserved1`.
def get_transaction_header_size():
    return 4 + 4 + 64 + 32 + 4

# Included fields are the transaction header, `version`,
# `network`, `type`, `maxFee` and `deadline`
def get_transaction_body_index():
    return get_transaction_header_size() + 1 + 1 + 2 + 8 + 8

def is_aggregate_transaction(tx_type):
    return (tx_type == NEM2_TRANSACTION_TYPE_AGGREGATE_BONDED or
        tx_type == NEM2_TRANSACTION_TYPE_AGGREGATE_COMPLETE)

def get_signing_bytes(payload_buffer_without_header, generation_hash_bytes, tx_type):
    print('payload_buffer_without_header', hexlify(payload_buffer_without_header))
    if is_aggregate_transaction(tx_type):
        return generation_hash_bytes + payload_buffer_without_header[:52]
    return generation_hash_bytes + payload_buffer_without_header

async def sign_tx(ctx, msg: NEM2SignTx, keychain):
    validate(msg)

    await validate_path(
        ctx,
        validate_nem2_path,
        keychain,
        msg.address_n,
        CURVE,
    )

    node = keychain.derive(msg.address_n, CURVE)

    if msg.cosigning:
        resp = NEM2CosignatureSignedTx()
        resp.parent_hash = unhexlify(msg.cosigning)
        resp.signature = ed25519.sign(node.private_key(), unhexlify(msg.cosigning), NEM2_HASH_ALG)
        return resp

    if msg.multisig:
        public_key = msg.multisig.signer
        common = msg.multisig
        await multisig.ask(ctx, msg)
    else:
        public_key = seed.remove_ed25519_prefix(node.public_key())
        common = msg.transaction

    if msg.transfer:
        tx = await transfer.transfer(ctx, common, msg.transfer)
    elif msg.mosaic_definition:
        tx = await mosaic.mosaic_definition(ctx, common, msg.mosaic_definition)
    elif msg.mosaic_supply:
        tx = await mosaic.mosaic_supply(ctx, common, msg.mosaic_supply)
    elif msg.namespace_registration:
        tx = await namespace.namespace_registration(ctx, common, msg.namespace_registration)
    elif msg.address_alias:
        tx = await namespace.address_alias(ctx, common, msg.address_alias)
    elif msg.namespace_metadata:
        tx = await metadata.metadata(ctx, common, msg.namespace_metadata)
    elif msg.mosaic_metadata:
        tx = await metadata.metadata(ctx, common, msg.mosaic_metadata)
    elif msg.account_metadata:
        tx = await metadata.metadata(ctx, common, msg.account_metadata)
    elif msg.mosaic_alias:
        tx = await namespace.mosaic_alias(ctx, common, msg.mosaic_alias)
    elif msg.aggregate:
        tx = await aggregate.aggregate(ctx, common, msg.aggregate)
    elif msg.hash_lock:
        tx = await hash_lock.hash_lock(ctx, common, msg.hash_lock)
    elif msg.secret_lock:
        tx = await secret_lock.secret_lock(ctx, common, msg.secret_lock)
    elif msg.secret_proof:
        tx = await secret_lock.secret_proof(ctx, common, msg.secret_proof)
    elif msg.multisig_modification:
        tx = await multisig.multisig_modification(ctx, common, msg.multisig_modification)
    elif msg.account_address_restriction:
        tx = await account_restriction.account_restriction(ctx, common, msg.account_address_restriction)
    elif msg.account_mosaic_restriction:
        tx = await account_restriction.account_restriction(ctx, common, msg.account_mosaic_restriction)
    elif msg.account_operation_restriction:
        tx = await account_restriction.account_restriction(ctx, common, msg.account_operation_restriction)
    else:
        raise ValueError("No transaction provided")

    if msg.multisig:
        # wrap transaction in multisig wrapper
        if msg.cosigning:
            tx = multisig.cosign(
                seed.remove_ed25519_prefix(node.public_key()),
                msg.transaction,
                tx,
                msg.multisig.signer,
            )
        else:
            tx = multisig.initiate(
                seed.remove_ed25519_prefix(node.public_key()), msg.transaction, tx
            )

    # https://nemtech.github.io/concepts/transaction.html#signing-a-transaction
    # sign tx
    generation_hash_bytes = unhexlify(msg.generation_hash)
    # Will be used for calculating signed payload, and subsequent hash.
    payload_without_header = tx[get_transaction_header_size():]

    signing_bytes = get_signing_bytes(payload_without_header, generation_hash_bytes, msg.transaction.type)
    signature = ed25519.sign(node.private_key(), signing_bytes, NEM2_HASH_ALG)

    # prepare payload
    payload = tx[:8] + signature + public_key + tx[104:]

    # 1) Take "R" part of a signature (first 32 bytes)
    first_half_of_sig = payload[8:40]
    # 2) Add public key to match sign/verify behavior (32 bytes)
    signer = payload[72:104]
    # 3) add transaction data without header (EntityDataBuffer)
    transaction_body = payload_without_header
    # In case of aggregate transactions, we hash only the merkle transaction hash.
    if is_aggregate_transaction(msg.transaction.type):
        transaction_body = tx[get_transaction_header_size():get_transaction_body_index() + 32]
    # 4) Add all the parts together
    # layout: `signature_R || signerPublicKey || generationHash || EntityDataBuffer`
    hash_bytes = first_half_of_sig + signer + generation_hash_bytes + transaction_body

    resp = NEM2SignedTx()
    resp.payload = payload
    resp.hash = sha3_256(hash_bytes).digest()
    resp.signature = signature
    return resp