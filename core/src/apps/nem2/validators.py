from trezor.messages.NEM2SignTx import (
    NEM2SignTx,
    NEM2TransactionCommon,
    NEM2TransferTransaction,
)
from trezor.wire import ProcessError

from .helpers import (
    NEM2_MAX_DIVISIBILITY,
    NEM2_MAX_ENCRYPTED_PAYLOAD_SIZE,
    NEM2_MAX_PLAIN_PAYLOAD_SIZE,
    NEM2_MAX_SUPPLY,
    NEM2_NETWORK_MAIN_NET,
    NEM2_NETWORK_MIJIN,
    NEM2_NETWORK_TEST_NET,
    NEM2_PUBLIC_KEY_SIZE,
)

from .namespace.validators import (
    _validate_namespace_registration,
    _validate_address_alias
)

def validate(msg: NEM2SignTx):
    if msg.transaction is None:
        raise ProcessError("No common transaction fields provided")

    _validate_single_tx(msg)
    _validate_common(msg.transaction)

    if msg.multisig:
        _validate_common(msg.multisig, True)
        _validate_multisig(msg.multisig, msg.transaction.version)
    if not msg.multisig and msg.cosigning:
        raise ProcessError("No multisig transaction to cosign")

    if msg.transfer:
        _validate_transfer(msg.transfer, msg.transaction.version)
    if(msg.namespace_registration):
        _validate_namespace_registration(msg.namespace_registration, msg.transaction.version)
    if(msg.address_alias):
        _validate_address_alias(msg.address_alias, msg.transaction.version)

def _validate_single_tx(msg: NEM2SignTx):
    # ensure exactly one transaction is provided
    tx_count = (
        bool(msg.transfer)
        + bool(msg.namespace_registration)
        + bool(msg.mosaic_definition)
        + bool(msg.mosaic_supply)
        + bool(msg.address_alias)
        + bool(msg.namespace_metadata)
        # + bool(msg.importance_transfer)
    )
    if tx_count == 0:
        raise ProcessError("No transaction provided")
    if tx_count > 1:
        raise ProcessError("More than one transaction provided")


def _validate_common(common: NEM2TransactionCommon, inner: bool = False):

    err = None
    if common.type is None:
        err = "type"
    if common.network_type is None:
        err = "network_type"
    if common.version is None:
        err = "version"
    if common.max_fee is None:
        err = "max_fee"
    if common.deadline is None:
        err = "deadline"

    if err:
        raise ProcessError("No %s provided" % err)


def _validate_multisig(multisig: NEM2TransactionCommon, version: int):
    if multisig.version != version:
        raise ProcessError("Inner transaction network is different")
    _validate_public_key(multisig.signer, "Invalid multisig signer public key provided")

def _validate_transfer(transfer: NEM2TransferTransaction, version: int):
    if transfer.recipient_address is None:
        raise ProcessError("No recipient provided")

    # TODO: replace C implementation of validate_address with something new for nem2
    # if not nem2.validate_address(transfer.recipient_address, network):
    #     raise ProcessError("Invalid recipient address")

    for m in transfer.mosaics:
        if m.id is None:
            raise ProcessError("No mosaic id provided")
        if m.amount is None:
            raise ProcessError("No mosaic amount provided")