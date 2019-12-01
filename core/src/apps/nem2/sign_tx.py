from trezor.crypto.curve import ed25519
from trezor.crypto.hashlib import sha3_256
from trezor.messages.NEM2SignedTx import NEM2SignedTx
from trezor.messages.NEM2SignTx import NEM2SignTx
from ubinascii import unhexlify, hexlify

from apps.common import seed
from apps.common.paths import validate_path
from apps.nem2 import CURVE, transfer, mosaic, namespace
from apps.nem2.helpers import NEM2_HASH_ALG, check_path, NEM2_TRANSACTION_TYPE_AGGREGATE_BONDED, NEM2_TRANSACTION_TYPE_AGGREGATE_COMPLETE
from apps.nem2.validators import validate


async def sign_tx(ctx, msg: NEM2SignTx, keychain):
    print("signing nem2 transaction", msg)
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

    print(msg)

    if msg.transfer:
        tx = await transfer.transfer(ctx, public_key, common, msg.transfer)
    elif msg.mosaic_definition:
        tx = await mosaic.mosaic_definition(ctx, public_key, common, msg.mosaic_definition)
    elif msg.mosaic_supply:
        tx = await mosaic.mosaic_supply(ctx, common, msg.mosaic_supply)
    elif msg.namespace_registration:
        tx = await namespace.namespace_registration(ctx, public_key, common, msg.namespace_registration)
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
    # signing bytes (all tx data expect size, signature and signer)
    # everything after the first 108 bytes of serialised transaction
    signing_bytes = tx[108:]

    # sign tx
    generation_hash_bytes = unhexlify(msg.generation_hash)
    signature = ed25519.sign(node.private_key(), generation_hash_bytes + signing_bytes, NEM2_HASH_ALG)

    # prepare payload
    payload = tx[:8] + signature + public_key + tx[104:]

    # prepare hash content
    payload_without_header = payload[108:]
    data_bytes = generation_hash_bytes + payload_without_header
    if msg.transaction.type == NEM2_TRANSACTION_TYPE_AGGREGATE_BONDED or msg.transaction.type == NEM2_TRANSACTION_TYPE_AGGREGATE_COMPLETE:
        data_bytes = generation_hash_bytes + payload_without_header[0:52]

    first_half_of_sig = payload[8:40]
    signer = payload[72:104]
    hash_bytes = first_half_of_sig + signer + data_bytes

    resp = NEM2SignedTx()
    resp.payload = payload
    resp.hash = sha3_256(hash_bytes, keccak=True).digest()
    return resp