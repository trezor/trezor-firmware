from typing import TYPE_CHECKING

from trezor.wire import ProcessError

if TYPE_CHECKING:
    from trezor.messages import NEMSignTx, NEMTransactionCommon


def validate(msg: NEMSignTx) -> None:
    from trezor.crypto import nem
    from trezor.enums import NEMModificationType
    from trezor.wire import ProcessError  # local_cache_global

    from .helpers import (
        NEM_MAX_DIVISIBILITY,
        NEM_MAX_ENCRYPTED_PAYLOAD_SIZE,
        NEM_MAX_PLAIN_PAYLOAD_SIZE,
        NEM_MAX_SUPPLY,
    )

    validate_address = nem.validate_address  # local_cache_attribute
    transfer = msg.transfer  # local_cache_attribute
    aggregate_modification = msg.aggregate_modification  # local_cache_attribute
    multisig = msg.multisig  # local_cache_attribute
    mosaic_creation = msg.mosaic_creation  # local_cache_attribute
    network = msg.transaction.network  # local_cache_attribute

    # _validate_single_tx
    # ensure exactly one transaction is provided
    tx_count = (
        bool(transfer)
        + bool(msg.provision_namespace)
        + bool(mosaic_creation)
        + bool(msg.supply_change)
        + bool(aggregate_modification)
        + bool(msg.importance_transfer)
    )
    if tx_count == 0:
        raise ProcessError("No transaction provided")
    if tx_count > 1:
        raise ProcessError("More than one transaction provided")

    _validate_common(msg.transaction)

    if multisig:
        _validate_common(multisig, True)
        # _validate_multisig
        if multisig.network != network:
            raise ProcessError("Inner transaction network is different")
        _validate_public_key(
            multisig.signer, "Invalid multisig signer public key provided"
        )
        # END _validate_multisig
    if not multisig and msg.cosigning:
        raise ProcessError("No multisig transaction to cosign")

    if transfer:
        payload = transfer.payload  # local_cache_attribute

        if transfer.public_key is not None:
            _validate_public_key(transfer.public_key, "Invalid recipient public key")
            if not payload:
                raise ProcessError("Public key provided but no payload to encrypt")

        if payload:
            if len(payload) > NEM_MAX_PLAIN_PAYLOAD_SIZE:
                raise ProcessError("Payload too large")
            if transfer.public_key and len(payload) > NEM_MAX_ENCRYPTED_PAYLOAD_SIZE:
                raise ProcessError("Payload too large")

        if not validate_address(transfer.recipient, network):
            raise ProcessError("Invalid recipient address")
        # END _validate_transfer
    if msg.provision_namespace:
        # _validate_provision_namespace
        if not validate_address(msg.provision_namespace.sink, network):
            raise ProcessError("Invalid rental sink address")
        # END _validate_provision_namespace
    if mosaic_creation:
        # _validate_mosaic_creation
        if not validate_address(mosaic_creation.sink, network):
            raise ProcessError("Invalid creation sink address")
        definition = mosaic_creation.definition  # local_cache_attribute
        supply = definition.supply  # local_cache_attribute
        divisibility = definition.divisibility  # local_cache_attribute

        if definition.name is not None:
            raise ProcessError("Name not allowed in mosaic creation transactions")
        if definition.ticker is not None:
            raise ProcessError("Ticker not allowed in mosaic creation transactions")
        if definition.networks:
            raise ProcessError("Networks not allowed in mosaic creation transactions")

        if supply is not None and divisibility is None:
            raise ProcessError(
                "Definition divisibility needs to be provided when supply is"
            )
        if supply is None and divisibility is not None:
            raise ProcessError(
                "Definition supply needs to be provided when divisibility is"
            )

        if definition.levy is not None:
            if definition.fee is None:
                raise ProcessError("No levy fee provided")
            if definition.levy_address is None:
                raise ProcessError("No levy address provided")
            if definition.levy_namespace is None:
                raise ProcessError("No levy namespace provided")
            if definition.levy_mosaic is None:
                raise ProcessError("No levy mosaic name provided")

            if divisibility is None:
                raise ProcessError("No divisibility provided")
            if supply is None:
                raise ProcessError("No supply provided")
            if definition.mutable_supply is None:
                raise ProcessError("No supply mutability provided")
            if definition.transferable is None:
                raise ProcessError("No mosaic transferability provided")
            if definition.description is None:
                raise ProcessError("No description provided")

            if divisibility > NEM_MAX_DIVISIBILITY:
                raise ProcessError("Invalid divisibility provided")
            if supply > NEM_MAX_SUPPLY:
                raise ProcessError("Invalid supply provided")

            if not validate_address(definition.levy_address, network):
                raise ProcessError("Invalid levy address")
        # END _validate_mosaic_creation
    if msg.supply_change:
        # _validate_supply_change
        pass
        # END _validate_supply_change
    if aggregate_modification:
        # _validate_aggregate_modification
        creation = multisig is None
        if creation and not aggregate_modification.modifications:
            raise ProcessError("No modifications provided")

        for m in aggregate_modification.modifications:
            if (
                creation
                and m.type == NEMModificationType.CosignatoryModification_Delete
            ):
                raise ProcessError("Cannot remove cosignatory when converting account")
            _validate_public_key(
                m.public_key, "Invalid cosignatory public key provided"
            )
        # END _validate_aggregate_modification
    if msg.importance_transfer:
        # _validate_importance_transfer
        _validate_public_key(
            msg.importance_transfer.public_key,
            "Invalid remote account public key provided",
        )
        # END _validate_importance_transfer


def validate_network(network: int) -> None:
    from .helpers import NEM_NETWORK_MAINNET, NEM_NETWORK_MIJIN, NEM_NETWORK_TESTNET

    if network not in (NEM_NETWORK_MAINNET, NEM_NETWORK_TESTNET, NEM_NETWORK_MIJIN):
        raise ProcessError("Invalid NEM network")


def _validate_common(common: NEMTransactionCommon, inner: bool = False) -> None:
    validate_network(common.network)
    signer = common.signer  # local_cache_attribute

    err = None

    if not inner and signer:
        raise ProcessError("Signer not allowed in outer transaction")

    if inner and signer is None:
        err = "signer"

    if err:
        if inner:
            raise ProcessError(f"No {err} provided in inner transaction")
        else:
            raise ProcessError(f"No {err} provided")

    if signer is not None:
        _validate_public_key(signer, "Invalid signer public key in inner transaction")


def _validate_public_key(public_key: bytes | None, err_msg: str) -> None:
    from .helpers import NEM_PUBLIC_KEY_SIZE

    if not public_key:
        raise ProcessError(f"{err_msg} (none provided)")
    if len(public_key) != NEM_PUBLIC_KEY_SIZE:
        raise ProcessError(f"{err_msg} (invalid length)")
