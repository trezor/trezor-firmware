from trezor.messages.NEM2SignTx import (
    NEM2SignTx,
    NEM2TransactionCommon,
    NEM2TransferTransaction,
    NEM2HashLockTransaction
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
    NEM2_NETWORK_MIJIN_TEST,
    NEM2_PUBLIC_KEY_SIZE,
    NEM2_SECRET_LOCK_SHA3_256,
    NEM2_SECRET_LOCK_KECCAK_256,
    NEM2_SECRET_LOCK_HASH_160,
    NEM2_SECRET_LOCK_HASH_256,
    NEM2_ALIAS_ACTION_TYPE_LINK,
    NEM2_ALIAS_ACTION_TYPE_UNLINK,
    NEM2_MOSAIC_SUPPLY_CHANGE_ACTION_INCREASE,
    NEM2_MOSAIC_SUPPLY_CHANGE_ACTION_DECREASE,
    NEM2_ACCOUNT_RESTRICTION_ALLOW_INCOMING_ADDRESS,
    NEM2_ACCOUNT_RESTRICTION_ALLOW_MOSAIC,
    NEM2_ACCOUNT_RESTRICTION_ALLOW_INCOMING_TRANSACTION_TYPE,
    NEM2_ACCOUNT_RESTRICTION_ALLOW_OUTGOING_ADDRESS,
    NEM2_ACCOUNT_RESTRICTION_ALLOW_OUTGOING_TRANSACTION_TYPE,
    NEM2_ACCOUNT_RESTRICTION_BLOCK_INCOMING_ADDRESS,
    NEM2_ACCOUNT_RESTRICTION_BLOCK_MOSAIC,
    NEM2_ACCOUNT_RESTRICTION_BLOCK_INCOMING_TRANSACTION_TYPE,
    NEM2_ACCOUNT_RESTRICTION_BLOCK_OUTGOING_ADDRESS,
    NEM2_ACCOUNT_RESTRICTION_BLOCK_OUTGOING_TRANSACTION_TYPE,
)

from .namespace.validators import (
    _validate_namespace_registration,
    _validate_address_alias
)

from .metadata.validators import _validate_metadata

def validate(msg: NEM2SignTx):
    if not validate_nem2_path(msg.address_n):
        raise ProcessError("Invalid HD path provided, must fit 'm/44\'/43\'/a'")

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
    if msg.mosaic_definition:
        _validate_mosaic_definition(msg.mosaic_definition)
    if msg.mosaic_supply:
        _validate_mosaic_supply(msg.mosaic_supply)
    if msg.namespace_registration:
        _validate_namespace_registration(msg.namespace_registration, msg.transaction.version)
    if msg.address_alias:
        _validate_address_alias(msg.address_alias, msg.transaction.version)
    if msg.mosaic_alias:
        _validate_mosaic_alias(msg.mosaic_alias, msg.transaction.version)
    if msg.namespace_metadata:
        _validate_metadata(msg.namespace_metadata, msg.transaction.type)
    if msg.mosaic_metadata:
        _validate_metadata(msg.mosaic_metadata, msg.transaction.type)
    if msg.account_metadata:
        _validate_metadata(msg.account_metadata, msg.transaction.type)
    if msg.hash_lock:
        _validate_hash_lock(msg.hash_lock)
    if msg.secret_lock:
        _validate_secret_lock(msg.secret_lock)
    if msg.secret_proof:
        _validate_secret_proof(msg.secret_proof)
    if msg.account_address_restriction:
        _validate_account_address_restriction(msg.account_address_restriction)
    if msg.account_mosaic_restriction:
        _validate_account_mosaic_restriction(msg.account_mosaic_restriction)
    if msg.account_operation_restriction:
        _validate_account_operation_restriction(msg.account_operation_restriction)

def _validate_single_tx(msg: NEM2SignTx):
    # ensure exactly one transaction is provided
    tx_count = (
        bool(msg.transfer)
        + bool(msg.namespace_registration)
        + bool(msg.mosaic_definition)
        + bool(msg.mosaic_supply)
        + bool(msg.address_alias)
        + bool(msg.namespace_metadata)
        + bool(msg.mosaic_metadata)
        + bool(msg.account_metadata)
        + bool(msg.mosaic_alias)
        + bool(msg.aggregate)
        + bool(msg.hash_lock)
        + bool(msg.secret_lock)
        + bool(msg.secret_proof)
        + bool(msg.multisig_modification)
        + bool(msg.account_address_restriction)
        + bool(msg.account_mosaic_restriction)
        + bool(msg.account_operation_restriction)
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

def address_validator(address_data):
    address = address_data.address
    network_type = address_data.network_type
    if len(address) != 40:
        raise ProcessError("Address must be 40 characters long")

    # Check address matches network type
    first_char = address[0]
    if first_char.upper() == 'S':
        if network_type != NEM2_NETWORK_MIJIN_TEST:
            raise ProcessError("Network type for address is invalid. Must be Mijin Test")
    elif first_char.upper() == 'M':
        if network_type != NEM2_NETWORK_MIJIN:
            raise ProcessError("Network type for address is invalid. Must be Mijin")
    elif first_char.upper() == 'T':
        if network_type != NEM2_NETWORK_TEST_NET:
            raise ProcessError("Network type for address is invalid. Must be Test Net")
    elif first_char.upper() == 'N':
        if network_type != NEM2_NETWORK_MAIN_NET:
            raise ProcessError("Network type for address is invalid. Must be Main Net")
    else:
        raise ProcessError("Address network is unsupported")

def validate_recipient_address(recipient_address):
    if recipient_address is None:
        raise ProcessError("No recipient provided")
    if recipient_address.address is None:
        raise ProcessError("No address provided")
    if recipient_address.network_type is None:
        raise ProcessError("No address network type provided")

def _validate_multisig(multisig: NEM2TransactionCommon, version: int):
    if multisig.version != version:
        raise ProcessError("Inner transaction network is different")
    _validate_public_key(multisig.signer, "Invalid multisig signer public key provided")

def _validate_transfer(transfer: NEM2TransferTransaction, version: int):
    validate_recipient_address(transfer.recipient_address)

    if transfer.message is None:
        raise ProcessError("No message provided")

    address_validator(transfer.recipient_address)

    for m in transfer.mosaics:
        if m.id is None:
            raise ProcessError("No mosaic id provided")
        if m.amount is None:
            raise ProcessError("No mosaic amount provided")

def _validate_mosaic_definition(mosaic_definition: NEM2MosaicDefinitionTransaction):
    if mosaic_definition.mosaic_id is None:
        raise ProcessError("No mosaic ID provided")
    if mosaic_definition.duration is None:
        raise ProcessError("No duration provided")
    if mosaic_definition.flags is None:
        raise ProcessError("No flags provided")
    if mosaic_definition.nonce is None:
        raise ProcessError("No nonce provided")
    if mosaic_definition.divisibility is None:
        raise ProcessError("No divisibility provided")

def _validate_mosaic_supply(mosaic_supply: NEM2MosaicSupplyChangeTransaction):
    if mosaic_supply.mosaic_id is None:
        raise ProcessError("No mosaic ID provided")
    if mosaic_supply.action is None:
        raise ProcessError("No action provided")
    if mosaic_supply.delta is None:
        raise ProcessError("No delta provided")

    # Action was provided, now check it is valid
    valid_actions = [NEM2_MOSAIC_SUPPLY_CHANGE_ACTION_INCREASE, NEM2_MOSAIC_SUPPLY_CHANGE_ACTION_DECREASE]
    if mosaic_supply.action not in valid_actions:
        raise ProcessError("Invalid action provided")

def _validate_mosaic_alias(mosaic_alias: NEM2MosaicAliasTransaction, network: int):
    if mosaic_alias.namespace_id is None:
        raise ProcessError("No namespace ID provided")
    if mosaic_alias.mosaic_id is None:
        raise ProcessError("No mosiac ID provided")
    if mosaic_alias.alias_action is None:
        raise ProcessError("No alias action provided")

    # Alais action was provided, now check it is valid
    valid_actions = [NEM2_ALIAS_ACTION_TYPE_LINK, NEM2_ALIAS_ACTION_TYPE_UNLINK]
    if mosaic_alias.alias_action not in valid_actions:
        raise ProcessError("Invalid alias action provided")

def _validate_hash_lock(hash_lock: NEM2HashLockTransaction):
    if hash_lock.mosaic is None:
        raise ProcessError("No mosaic provided")
    if hash_lock.duration is None:
        raise ProcessError("No duration provided")
    if hash_lock.hash is None:
        raise ProcessError("No AggregateTransaction hash provided")

def _validate_secret_lock(secret_lock: NEM2SecretLockTransaction):
    if secret_lock.secret is None:
        raise ProcessError("No secret provided")
    if secret_lock.mosaic is None:
        raise ProcessError("No mosaic provided")
    if secret_lock.duration is None:
        raise ProcessError("No duration provided")
    if secret_lock.hash_algorithm is None:
        raise ProcessError("No hash algorithm provided")

    validate_recipient_address(secret_lock.recipient_address)
    validate_secret(secret_lock.secret, secret_lock.hash_algorithm)

def _validate_secret_proof(secret_lock: NEM2SecretProofTransaction):
    if secret_lock.secret is None:
        raise ProcessError("No secret provided")
    if secret_lock.proof is None:
        raise ProcessError("No proof provided")
    if secret_lock.hash_algorithm is None:
        raise ProcessError("No hash algorithm provided")

    validate_recipient_address(secret_lock.recipient_address)
    validate_secret(secret_lock.secret, secret_lock.hash_algorithm)

def validate_secret(secret, hash_algorithm):
    if (hash_algorithm == NEM2_SECRET_LOCK_SHA3_256 or
        hash_algorithm == NEM2_SECRET_LOCK_KECCAK_256 or
        hash_algorithm == NEM2_SECRET_LOCK_HASH_256):
        if len(secret) != 64:
            raise ProcessError("Secret must be of length 64 (was {})".format(len(secret)))
    elif hash_algorithm == NEM2_SECRET_LOCK_HASH_160:
        if len(secret) != 40 or len(secret) != 64:
            raise ProcessError("Secret must be of length 40 or 64 (was {})".format(len(secret)))
    else:
        raise ProcessError("Invalid hash algorithm selected")

def _validate_account_address_restriction(account_address_restriction: NEM2AccountAddressRestrictionTransaction):

    valid_restriction_types = [
        NEM2_ACCOUNT_RESTRICTION_ALLOW_INCOMING_ADDRESS,
        NEM2_ACCOUNT_RESTRICTION_ALLOW_OUTGOING_ADDRESS,
        NEM2_ACCOUNT_RESTRICTION_BLOCK_INCOMING_ADDRESS,
        NEM2_ACCOUNT_RESTRICTION_BLOCK_OUTGOING_ADDRESS
    ]

    if account_address_restriction.restriction_type is None:
        raise ProcessError("No restriction type provided")
    if account_address_restriction.restriction_type not in valid_restriction_types:
        raise ProcessError("Restriction type is invalid")
    if account_address_restriction.restriction_additions is None:
        raise ProcessError("No restriction additions provided")
    if account_address_restriction.restriction_deletions is None:
        raise ProcessError("No restriction deletions provided")

def _validate_account_mosaic_restriction(account_mosaic_restriction: NEM2AccountMosaicRestrictionTransaction):

    valid_restriction_types = [
        NEM2_ACCOUNT_RESTRICTION_ALLOW_MOSAIC,
        NEM2_ACCOUNT_RESTRICTION_BLOCK_MOSAIC,
    ]

    if account_mosaic_restriction.restriction_type is None:
        raise ProcessError("No restriction type provided")
    if account_mosaic_restriction.restriction_type not in valid_restriction_types:
        raise ProcessError("Restriction type is invalid")
    if account_mosaic_restriction.restriction_additions is None:
        raise ProcessError("No restriction additions provided")
    if account_mosaic_restriction.restriction_deletions is None:
        raise ProcessError("No restriction deletions provided")

def _validate_account_operation_restriction(account_operation_restriction: NEM2AccountOperationRestrictionTransaction):

    valid_restriction_types = [
        NEM2_ACCOUNT_RESTRICTION_ALLOW_INCOMING_TRANSACTION_TYPE,
        NEM2_ACCOUNT_RESTRICTION_ALLOW_OUTGOING_TRANSACTION_TYPE,
        NEM2_ACCOUNT_RESTRICTION_BLOCK_INCOMING_TRANSACTION_TYPE,
        NEM2_ACCOUNT_RESTRICTION_BLOCK_OUTGOING_TRANSACTION_TYPE
    ]

    if account_operation_restriction.restriction_type is None:
        raise ProcessError("No restriction type provided")
    if account_operation_restriction.restriction_type not in valid_restriction_types:
        raise ProcessError("Restriction type is invalid")
    if account_operation_restriction.restriction_additions is None:
        raise ProcessError("No restriction additions provided")
    if account_operation_restriction.restriction_deletions is None:
        raise ProcessError("No restriction deletions provided")
