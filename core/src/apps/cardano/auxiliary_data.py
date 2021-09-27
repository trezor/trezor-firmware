from trezor.crypto import hashlib
from trezor.crypto.curve import ed25519
from trezor.enums import CardanoAddressType, CardanoTxAuxiliaryDataSupplementType
from trezor.messages import CardanoTxAuxiliaryDataSupplement

from apps.common import cbor

from .address import (
    derive_address_bytes,
    derive_human_readable_address,
    validate_address_parameters,
)
from .helpers import INVALID_AUXILIARY_DATA, bech32
from .helpers.bech32 import HRP_JORMUN_PUBLIC_KEY
from .helpers.paths import SCHEMA_STAKING_ANY_ACCOUNT
from .helpers.utils import derive_public_key
from .layout import confirm_catalyst_registration, show_auxiliary_data_hash

if False:
    from typing import Union
    from trezor import wire

    from trezor.messages import (
        CardanoCatalystRegistrationParametersType,
        CardanoTxAuxiliaryData,
    )

    CatalystRegistrationPayload = dict[int, Union[bytes, int]]
    SignedCatalystRegistrationPayload = tuple[CatalystRegistrationPayload, bytes]
    CatalystRegistrationSignature = dict[int, bytes]
    CatalystRegistration = dict[
        int, Union[CatalystRegistrationPayload, CatalystRegistrationSignature]
    ]

    from . import seed

AUXILIARY_DATA_HASH_SIZE = 32
CATALYST_VOTING_PUBLIC_KEY_LENGTH = 32
CATALYST_REGISTRATION_HASH_SIZE = 32

METADATA_KEY_CATALYST_REGISTRATION = 61284
METADATA_KEY_CATALYST_REGISTRATION_SIGNATURE = 61285


def validate_auxiliary_data(auxiliary_data: CardanoTxAuxiliaryData) -> None:
    fields_provided = 0
    if auxiliary_data.hash:
        fields_provided += 1
        _validate_auxiliary_data_hash(auxiliary_data.hash)
    if auxiliary_data.catalyst_registration_parameters:
        fields_provided += 1
        _validate_catalyst_registration_parameters(
            auxiliary_data.catalyst_registration_parameters
        )

    if fields_provided != 1:
        raise INVALID_AUXILIARY_DATA


def _validate_auxiliary_data_hash(auxiliary_data_hash: bytes) -> None:
    if len(auxiliary_data_hash) != AUXILIARY_DATA_HASH_SIZE:
        raise INVALID_AUXILIARY_DATA


def _validate_catalyst_registration_parameters(
    catalyst_registration_parameters: CardanoCatalystRegistrationParametersType,
) -> None:
    if (
        len(catalyst_registration_parameters.voting_public_key)
        != CATALYST_VOTING_PUBLIC_KEY_LENGTH
    ):
        raise INVALID_AUXILIARY_DATA

    if not SCHEMA_STAKING_ANY_ACCOUNT.match(
        catalyst_registration_parameters.staking_path
    ):
        raise INVALID_AUXILIARY_DATA

    address_parameters = catalyst_registration_parameters.reward_address_parameters
    if address_parameters.address_type == CardanoAddressType.BYRON:
        raise INVALID_AUXILIARY_DATA

    validate_address_parameters(address_parameters)


async def show_auxiliary_data(
    ctx: wire.Context,
    keychain: seed.Keychain,
    auxiliary_data_hash: bytes,
    catalyst_registration_parameters: CardanoCatalystRegistrationParametersType | None,
    protocol_magic: int,
    network_id: int,
) -> None:
    if catalyst_registration_parameters:
        await _show_catalyst_registration(
            ctx,
            keychain,
            catalyst_registration_parameters,
            protocol_magic,
            network_id,
        )

    await show_auxiliary_data_hash(ctx, auxiliary_data_hash)


async def _show_catalyst_registration(
    ctx: wire.Context,
    keychain: seed.Keychain,
    catalyst_registration_parameters: CardanoCatalystRegistrationParametersType,
    protocol_magic: int,
    network_id: int,
) -> None:
    public_key = catalyst_registration_parameters.voting_public_key
    encoded_public_key = bech32.encode(HRP_JORMUN_PUBLIC_KEY, public_key)
    staking_path = catalyst_registration_parameters.staking_path
    reward_address = derive_human_readable_address(
        keychain,
        catalyst_registration_parameters.reward_address_parameters,
        protocol_magic,
        network_id,
    )
    nonce = catalyst_registration_parameters.nonce

    await confirm_catalyst_registration(
        ctx, encoded_public_key, staking_path, reward_address, nonce
    )


def get_auxiliary_data_hash_and_supplement(
    keychain: seed.Keychain,
    auxiliary_data: CardanoTxAuxiliaryData,
    protocol_magic: int,
    network_id: int,
) -> tuple[bytes, CardanoTxAuxiliaryDataSupplement]:
    if parameters := auxiliary_data.catalyst_registration_parameters:
        (
            catalyst_registration_payload,
            catalyst_signature,
        ) = _get_signed_catalyst_registration_payload(
            keychain, parameters, protocol_magic, network_id
        )
        auxiliary_data_hash = _get_catalyst_registration_auxiliary_data_hash(
            catalyst_registration_payload, catalyst_signature
        )
        auxiliary_data_supplement = CardanoTxAuxiliaryDataSupplement(
            type=CardanoTxAuxiliaryDataSupplementType.CATALYST_REGISTRATION_SIGNATURE,
            auxiliary_data_hash=auxiliary_data_hash,
            catalyst_signature=catalyst_signature,
        )
        return auxiliary_data_hash, auxiliary_data_supplement
    else:
        assert auxiliary_data.hash is not None  # validate_auxiliary_data
        return auxiliary_data.hash, CardanoTxAuxiliaryDataSupplement(
            type=CardanoTxAuxiliaryDataSupplementType.NONE
        )


def _get_catalyst_registration_auxiliary_data_hash(
    catalyst_registration_payload: CatalystRegistrationPayload,
    catalyst_registration_payload_signature: bytes,
) -> bytes:
    cborized_catalyst_registration = _cborize_catalyst_registration(
        catalyst_registration_payload,
        catalyst_registration_payload_signature,
    )
    return _hash_auxiliary_data(
        cbor.encode(_wrap_metadata(cborized_catalyst_registration))
    )


def _cborize_catalyst_registration(
    catalyst_registration_payload: CatalystRegistrationPayload,
    catalyst_registration_payload_signature: bytes,
) -> CatalystRegistration:
    catalyst_registration_signature = {1: catalyst_registration_payload_signature}

    return {
        METADATA_KEY_CATALYST_REGISTRATION: catalyst_registration_payload,
        METADATA_KEY_CATALYST_REGISTRATION_SIGNATURE: catalyst_registration_signature,
    }


def _get_signed_catalyst_registration_payload(
    keychain: seed.Keychain,
    catalyst_registration_parameters: CardanoCatalystRegistrationParametersType,
    protocol_magic: int,
    network_id: int,
) -> SignedCatalystRegistrationPayload:
    staking_key = derive_public_key(
        keychain, catalyst_registration_parameters.staking_path
    )

    payload: CatalystRegistrationPayload = {
        1: catalyst_registration_parameters.voting_public_key,
        2: staking_key,
        3: derive_address_bytes(
            keychain,
            catalyst_registration_parameters.reward_address_parameters,
            protocol_magic,
            network_id,
        ),
        4: catalyst_registration_parameters.nonce,
    }

    signature = _create_catalyst_registration_payload_signature(
        keychain,
        payload,
        catalyst_registration_parameters.staking_path,
    )

    return payload, signature


def _create_catalyst_registration_payload_signature(
    keychain: seed.Keychain,
    catalyst_registration_payload: CatalystRegistrationPayload,
    path: list[int],
) -> bytes:
    node = keychain.derive(path)

    encoded_catalyst_registration = cbor.encode(
        {METADATA_KEY_CATALYST_REGISTRATION: catalyst_registration_payload}
    )

    catalyst_registration_hash = hashlib.blake2b(
        data=encoded_catalyst_registration,
        outlen=CATALYST_REGISTRATION_HASH_SIZE,
    ).digest()

    return ed25519.sign_ext(
        node.private_key(), node.private_key_ext(), catalyst_registration_hash
    )


def _wrap_metadata(metadata: dict) -> tuple[dict, tuple]:
    """
    A new structure of metadata is used after Cardano Mary era. The metadata
    is wrapped in a tuple and auxiliary_scripts may follow it. Cardano
    tooling uses this new format of "wrapped" metadata even if no
    auxiliary_scripts are included. So we do the same here.

    https://github.com/input-output-hk/cardano-ledger-specs/blob/f7deb22be14d31b535f56edc3ca542c548244c67/shelley-ma/shelley-ma-test/cddl-files/shelley-ma.cddl#L212
    """
    return metadata, ()


def _hash_auxiliary_data(auxiliary_data: bytes) -> bytes:
    return hashlib.blake2b(
        data=auxiliary_data, outlen=AUXILIARY_DATA_HASH_SIZE
    ).digest()
