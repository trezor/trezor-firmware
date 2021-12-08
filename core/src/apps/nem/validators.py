from trezor.crypto import nem
from trezor.enums import NEMModificationType
from trezor.messages import (
    NEMAggregateModification,
    NEMImportanceTransfer,
    NEMMosaicCreation,
    NEMMosaicSupplyChange,
    NEMProvisionNamespace,
    NEMSignTx,
    NEMTransactionCommon,
    NEMTransfer,
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


def validate(msg: NEMSignTx) -> None:
    _validate_single_tx(msg)
    _validate_common(msg.transaction)

    if msg.multisig:
        _validate_common(msg.multisig, inner=True)
        _validate_multisig(msg.multisig, msg.transaction.network)
    if not msg.multisig and msg.cosigning:
        raise ProcessError("No multisig transaction to cosign")

    if msg.transfer:
        _validate_transfer(msg.transfer, msg.transaction.network)
    if msg.provision_namespace:
        _validate_provision_namespace(msg.provision_namespace, msg.transaction.network)
    if msg.mosaic_creation:
        _validate_mosaic_creation(msg.mosaic_creation, msg.transaction.network)
    if msg.supply_change:
        _validate_supply_change(msg.supply_change)
    if msg.aggregate_modification:
        _validate_aggregate_modification(
            msg.aggregate_modification, msg.multisig is None
        )
    if msg.importance_transfer:
        _validate_importance_transfer(msg.importance_transfer)


def validate_network(network: int) -> None:
    if network not in (NEM_NETWORK_MAINNET, NEM_NETWORK_TESTNET, NEM_NETWORK_MIJIN):
        raise ProcessError("Invalid NEM network")


def _validate_single_tx(msg: NEMSignTx) -> None:
    # ensure exactly one transaction is provided
    tx_count = (
        bool(msg.transfer)
        + bool(msg.provision_namespace)
        + bool(msg.mosaic_creation)
        + bool(msg.supply_change)
        + bool(msg.aggregate_modification)
        + bool(msg.importance_transfer)
    )
    if tx_count == 0:
        raise ProcessError("No transaction provided")
    if tx_count > 1:
        raise ProcessError("More than one transaction provided")


def _validate_common(common: NEMTransactionCommon, inner: bool = False) -> None:
    validate_network(common.network)

    err = None

    if not inner and common.signer:
        raise ProcessError("Signer not allowed in outer transaction")

    if inner and common.signer is None:
        err = "signer"

    if err:
        if inner:
            raise ProcessError(f"No {err} provided in inner transaction")
        else:
            raise ProcessError(f"No {err} provided")

    if common.signer is not None:
        _validate_public_key(
            common.signer, "Invalid signer public key in inner transaction"
        )


def _validate_public_key(public_key: bytes | None, err_msg: str) -> None:
    if not public_key:
        raise ProcessError(f"{err_msg} (none provided)")
    if len(public_key) != NEM_PUBLIC_KEY_SIZE:
        raise ProcessError(f"{err_msg} (invalid length)")


def _validate_importance_transfer(importance_transfer: NEMImportanceTransfer) -> None:
    _validate_public_key(
        importance_transfer.public_key, "Invalid remote account public key provided"
    )


def _validate_multisig(multisig: NEMTransactionCommon, network: int) -> None:
    if multisig.network != network:
        raise ProcessError("Inner transaction network is different")
    _validate_public_key(multisig.signer, "Invalid multisig signer public key provided")


def _validate_aggregate_modification(
    aggregate_modification: NEMAggregateModification, creation: bool = False
) -> None:

    if creation and not aggregate_modification.modifications:
        raise ProcessError("No modifications provided")

    for m in aggregate_modification.modifications:
        if creation and m.type == NEMModificationType.CosignatoryModification_Delete:
            raise ProcessError("Cannot remove cosignatory when converting account")
        _validate_public_key(m.public_key, "Invalid cosignatory public key provided")


def _validate_supply_change(supply_change: NEMMosaicSupplyChange) -> None:
    pass


def _validate_mosaic_creation(mosaic_creation: NEMMosaicCreation, network: int) -> None:
    if not nem.validate_address(mosaic_creation.sink, network):
        raise ProcessError("Invalid creation sink address")

    if mosaic_creation.definition.name is not None:
        raise ProcessError("Name not allowed in mosaic creation transactions")
    if mosaic_creation.definition.ticker is not None:
        raise ProcessError("Ticker not allowed in mosaic creation transactions")
    if mosaic_creation.definition.networks:
        raise ProcessError("Networks not allowed in mosaic creation transactions")

    if (
        mosaic_creation.definition.supply is not None
        and mosaic_creation.definition.divisibility is None
    ):
        raise ProcessError(
            "Definition divisibility needs to be provided when supply is"
        )
    if (
        mosaic_creation.definition.supply is None
        and mosaic_creation.definition.divisibility is not None
    ):
        raise ProcessError(
            "Definition supply needs to be provided when divisibility is"
        )

    if mosaic_creation.definition.levy is not None:
        if mosaic_creation.definition.fee is None:
            raise ProcessError("No levy fee provided")
        if mosaic_creation.definition.levy_address is None:
            raise ProcessError("No levy address provided")
        if mosaic_creation.definition.levy_namespace is None:
            raise ProcessError("No levy namespace provided")
        if mosaic_creation.definition.levy_mosaic is None:
            raise ProcessError("No levy mosaic name provided")

        if mosaic_creation.definition.divisibility is None:
            raise ProcessError("No divisibility provided")
        if mosaic_creation.definition.supply is None:
            raise ProcessError("No supply provided")
        if mosaic_creation.definition.mutable_supply is None:
            raise ProcessError("No supply mutability provided")
        if mosaic_creation.definition.transferable is None:
            raise ProcessError("No mosaic transferability provided")
        if mosaic_creation.definition.description is None:
            raise ProcessError("No description provided")

        if mosaic_creation.definition.divisibility > NEM_MAX_DIVISIBILITY:
            raise ProcessError("Invalid divisibility provided")
        if mosaic_creation.definition.supply > NEM_MAX_SUPPLY:
            raise ProcessError("Invalid supply provided")

        if not nem.validate_address(mosaic_creation.definition.levy_address, network):
            raise ProcessError("Invalid levy address")


def _validate_provision_namespace(
    provision_namespace: NEMProvisionNamespace, network: int
) -> None:
    if not nem.validate_address(provision_namespace.sink, network):
        raise ProcessError("Invalid rental sink address")


def _validate_transfer(transfer: NEMTransfer, network: int) -> None:
    if transfer.public_key is not None:
        _validate_public_key(transfer.public_key, "Invalid recipient public key")
        if not transfer.payload:
            raise ProcessError("Public key provided but no payload to encrypt")

    if transfer.payload:
        if len(transfer.payload) > NEM_MAX_PLAIN_PAYLOAD_SIZE:
            raise ProcessError("Payload too large")
        if (
            transfer.public_key
            and len(transfer.payload) > NEM_MAX_ENCRYPTED_PAYLOAD_SIZE
        ):
            raise ProcessError("Payload too large")

    if not nem.validate_address(transfer.recipient, network):
        raise ProcessError("Invalid recipient address")
