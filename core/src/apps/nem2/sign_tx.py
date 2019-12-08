from trezor.crypto.curve import ed25519
from trezor.crypto.hashlib import sha3_256
from trezor.messages.NEM2SignedTx import NEM2SignedTx
from trezor.messages.NEM2SignTx import NEM2SignTx
from ubinascii import unhexlify, hexlify

from apps.common import seed
from apps.common.paths import validate_path
from apps.nem2 import CURVE, transfer, mosaic, aggregate
from apps.nem2.helpers import NEM2_HASH_ALG, check_path, NEM2_TRANSACTION_TYPE_AGGREGATE_BONDED, NEM2_TRANSACTION_TYPE_AGGREGATE_COMPLETE
from apps.nem2.validators import validate

# Included fields are `size`, `verifiableEntityHeader_Reserved1`,
# `signature`, `signerPublicKey` and `entityBody_Reserved1`.
def get_transaction_header_size():
    return 8 + 64 + 32 + 4

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
        check_path,
        keychain,
        msg.address_n,
        CURVE,
    )

    node = keychain.derive(msg.address_n, CURVE)

    if msg.multisig:
        public_key = msg.multisig.signer
        common = msg.multisig
        await multisig.ask(ctx, msg)
    else:
        public_key = seed.remove_ed25519_prefix(node.public_key())
        common = msg.transaction

    if msg.transfer:
        tx = await transfer.transfer(ctx, public_key, common, msg.transfer)
    elif msg.mosaic_definition:
        tx = await mosaic.mosaic_definition(ctx, public_key, common, msg.mosaic_definition)
    elif msg.mosaic_supply:
        tx = await mosaic.mosaic_supply(ctx, common, msg.mosaic_supply)
    elif msg.aggregate:
        tx = await aggregate.aggregate(ctx, common, msg.aggregate)
        # tx = await mosaic.mosaic_supply(ctx, common, msg.mosaic_supply)
    # elif msg.provision_namespace:
    #     tx = await namespace.namespace(ctx, public_key, common, msg.provision_namespace)
    # elif msg.supply_change:
    #     tx = await mosaic.supply_change(ctx, public_key, common, msg.supply_change)
    # elif msg.aggregate_modification:
    #     tx = await multisig.aggregate_modification(
    #         ctx,
    #         public_key,
    #         common,
    #         msg.aggregate_modification,
    #         msg.multisig is not None,
    #     )
    # elif msg.importance_transfer:
    #     tx = await transfer.importance_transfer(
    #         ctx, public_key, common, msg.importance_transfer
    #     )
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
    return resp