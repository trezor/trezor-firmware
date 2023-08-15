from typing import TYPE_CHECKING

from apps.common.keychain import with_slip44_keychain

from . import CURVE, PATTERNS, SLIP44_ID

if TYPE_CHECKING:
    from trezor.messages import NEMSignedTx, NEMSignTx

    from apps.common.keychain import Keychain


@with_slip44_keychain(*PATTERNS, slip44_id=SLIP44_ID, curve=CURVE)
async def sign_tx(msg: NEMSignTx, keychain: Keychain) -> NEMSignedTx:
    from trezor.crypto.curve import ed25519
    from trezor.messages import NEMSignedTx
    from trezor.wire import DataError

    from apps.common import seed
    from apps.common.paths import validate_path

    from . import mosaic, multisig, namespace, transfer
    from .helpers import NEM_HASH_ALG, check_path
    from .validators import validate

    validate(msg)
    msg_multisig = msg.multisig  # local_cache_attribute
    transaction = msg.transaction  # local_cache_attribute

    await validate_path(
        keychain,
        transaction.address_n,
        check_path(transaction.address_n, transaction.network),
    )

    node = keychain.derive(transaction.address_n)

    if msg_multisig:
        if msg_multisig.signer is None:
            raise DataError("No signer provided")
        public_key = msg_multisig.signer
        common = msg_multisig
        await multisig.ask(msg)
    else:
        public_key = seed.remove_ed25519_prefix(node.public_key())
        common = transaction

    if msg.transfer:
        tx = await transfer.transfer(public_key, common, msg.transfer, node)
    elif msg.provision_namespace:
        tx = await namespace.namespace(public_key, common, msg.provision_namespace)
    elif msg.mosaic_creation:
        tx = await mosaic.mosaic_creation(public_key, common, msg.mosaic_creation)
    elif msg.supply_change:
        tx = await mosaic.supply_change(public_key, common, msg.supply_change)
    elif msg.aggregate_modification:
        tx = await multisig.aggregate_modification(
            public_key,
            common,
            msg.aggregate_modification,
            msg_multisig is not None,
        )
    elif msg.importance_transfer:
        tx = await transfer.importance_transfer(
            public_key, common, msg.importance_transfer
        )
    else:
        raise DataError("No transaction provided")

    if msg_multisig:
        # wrap transaction in multisig wrapper
        if msg.cosigning:
            assert msg_multisig.signer is not None
            tx = multisig.cosign(
                seed.remove_ed25519_prefix(node.public_key()),
                transaction,
                tx,
                msg_multisig.signer,
            )
        else:
            tx = multisig.initiate(
                seed.remove_ed25519_prefix(node.public_key()), transaction, tx
            )

    signature = ed25519.sign(node.private_key(), tx, NEM_HASH_ALG)

    return NEMSignedTx(
        data=tx,
        signature=signature,
    )
