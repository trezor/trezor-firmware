from trezor.messages.NEM2SignTx import (
    NEM2SignTx,
    NEM2TransactionCommon,
    NEM2TransferTransaction,
)
from trezor.wire import ProcessError

from .helpers import (
    NEM_MAX_DIVISIBILITY,
    NEM_MAX_ENCRYPTED_PAYLOAD_SIZE,
    NEM_MAX_PLAIN_PAYLOAD_SIZE,
    NEM_MAX_SUPPLY,
    NEM_NETWORK_MAINNET,
    NEM_NETWORK_MIJIN,
    NEM_NETWORK_TESTNET,
    NEM_PUBLIC_KEY_SIZE,
)

def validate(msg: NEMSignTx):
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



def _validate_single_tx(msg: NEMSignTx):
    # ensure exactly one transaction is provided
    tx_count = (
        bool(msg.transfer)
        # + bool(msg.provision_namespace)
        # + bool(msg.mosaic_creation)
        # + bool(msg.supply_change)
        # + bool(msg.aggregate_modification)
        # + bool(msg.importance_transfer)
    )
    if tx_count == 0:
        raise ProcessError("No transaction provided")
    if tx_count > 1:
        raise ProcessError("More than one transaction provided")


def _validate_common(common: NEMTransactionCommon, inner: bool = False):

    err = None
    if common.fee is None:
        err = "fee"
    if common.deadline is None:
        err = "deadline"

    if not inner and common.signer_public_key:
        raise ProcessError("Signer not allowed in outer transaction")

    if inner and common.signer_public_key is None:
        err = "signer_public_key"

    if err:
        if inner:
            raise ProcessError("No %s provided in inner transaction" % err)
        else:
            raise ProcessError("No %s provided" % err)

    if common.signer_public_key is not None:
        _validate_public_key(
            common.signer_public_key, "Invalid sign_public_key in inner transaction"
        )


def _validate_public_key(public_key: bytes, err_msg: str):
    if not public_key:
        raise ProcessError("%s (none provided)" % err_msg)
    if len(public_key) != NEM_PUBLIC_KEY_SIZE:
        raise ProcessError("%s (invalid length)" % err_msg)

def _validate_multisig(multisig: NEMTransactionCommon, network: int):
    if multisig.network != network:
        raise ProcessError("Inner transaction network is different")
    _validate_public_key(multisig.signer, "Invalid multisig signer public key provided")

def _validate_transfer(transfer: NEMTransfer, network: int):
    if transfer.recipient_address is None:
        raise ProcessError("No recipient provided")

    # TODO: replace C implementation of validate_address with something new for nem2
    # if not nem2.validate_address(transfer.recipient_address, network):
    #     raise ProcessError("Invalid recipient address")

    for m in transfer.mosaics:
        if m.namespace is None:
            raise ProcessError("No mosaic namespace provided")
        if m.mosaic is None:
            raise ProcessError("No mosaic name provided")
        if m.quantity is None:
            raise ProcessError("No mosaic quantity provided")
