from micropython import const
from typing import TYPE_CHECKING

from trezor.crypto import hashlib
from trezor.enums import CardanoAddressType, CardanoCVoteRegistrationFormat

from apps.common import cbor

from . import addresses, layout
from .helpers.paths import SCHEMA_STAKING_ANY_ACCOUNT
from .helpers.utils import derive_public_key

if TYPE_CHECKING:
    Delegations = list[tuple[bytes, int]]
    CVoteRegistrationPayload = dict[int, Delegations | bytes | int]
    SignedCVoteRegistrationPayload = tuple[CVoteRegistrationPayload, bytes]

    from trezor import messages

    from . import seed

_AUXILIARY_DATA_HASH_SIZE = const(32)
_CVOTE_PUBLIC_KEY_LENGTH = const(32)
_CVOTE_REGISTRATION_HASH_SIZE = const(32)

_METADATA_KEY_CVOTE_REGISTRATION = const(61284)
_METADATA_KEY_CVOTE_REGISTRATION_SIGNATURE = const(61285)

_MAX_DELEGATION_COUNT = const(32)
_DEFAULT_VOTING_PURPOSE = const(0)


def assert_cond(condition: bool) -> None:
    from trezor import wire

    if not condition:
        raise wire.ProcessError("Invalid auxiliary data")


def validate(
    auxiliary_data: messages.CardanoTxAuxiliaryData,
    protocol_magic: int,
    network_id: int,
) -> None:
    fields_provided = 0
    if auxiliary_data.hash:
        fields_provided += 1
        # _validate_hash
        assert_cond(len(auxiliary_data.hash) == _AUXILIARY_DATA_HASH_SIZE)
    if auxiliary_data.cvote_registration_parameters:
        fields_provided += 1
        _validate_cvote_registration_parameters(
            auxiliary_data.cvote_registration_parameters,
            protocol_magic,
            network_id,
        )
    assert_cond(fields_provided == 1)


def _validate_cvote_registration_parameters(
    parameters: messages.CardanoCVoteRegistrationParametersType,
    protocol_magic: int,
    network_id: int,
) -> None:
    vote_key_fields_provided = 0
    if parameters.vote_public_key is not None:
        vote_key_fields_provided += 1
        _validate_vote_public_key(parameters.vote_public_key)
    if parameters.delegations:
        vote_key_fields_provided += 1
        assert_cond(parameters.format == CardanoCVoteRegistrationFormat.CIP36)
        _validate_delegations(parameters.delegations)
    assert_cond(vote_key_fields_provided == 1)

    assert_cond(SCHEMA_STAKING_ANY_ACCOUNT.match(parameters.staking_path))

    payment_address_fields_provided = 0
    if parameters.payment_address is not None:
        payment_address_fields_provided += 1
        addresses.validate_cvote_payment_address(
            parameters.payment_address, protocol_magic, network_id
        )
    if parameters.payment_address_parameters:
        payment_address_fields_provided += 1
        addresses.validate_cvote_payment_address_parameters(
            parameters.payment_address_parameters
        )
    assert_cond(payment_address_fields_provided == 1)

    if parameters.voting_purpose is not None:
        assert_cond(parameters.format == CardanoCVoteRegistrationFormat.CIP36)


def _validate_vote_public_key(key: bytes) -> None:
    assert_cond(len(key) == _CVOTE_PUBLIC_KEY_LENGTH)


def _validate_delegations(
    delegations: list[messages.CardanoCVoteDelegation],
) -> None:
    assert_cond(len(delegations) <= _MAX_DELEGATION_COUNT)
    for delegation in delegations:
        _validate_vote_public_key(delegation.vote_public_key)


def _get_voting_purpose_to_serialize(
    parameters: messages.CardanoCVoteRegistrationParametersType,
) -> int | None:
    if parameters.format == CardanoCVoteRegistrationFormat.CIP15:
        return None
    if parameters.voting_purpose is None:
        return _DEFAULT_VOTING_PURPOSE
    return parameters.voting_purpose


async def show(
    keychain: seed.Keychain,
    auxiliary_data_hash: bytes,
    parameters: messages.CardanoCVoteRegistrationParametersType | None,
    protocol_magic: int,
    network_id: int,
    should_show_details: bool,
) -> None:
    if parameters:
        await _show_cvote_registration(
            keychain,
            parameters,
            protocol_magic,
            network_id,
            should_show_details,
        )

    if should_show_details:
        await layout.show_auxiliary_data_hash(auxiliary_data_hash)


def _should_show_payment_warning(address_type: CardanoAddressType) -> bool:
    # For cvote payment addresses that are actually REWARD addresses, we show a warning that the
    # address is not eligible for rewards. https://github.com/cardano-foundation/CIPs/pull/373
    # However, the registration is otherwise valid, so we allow such addresses since we don't
    # want to prevent the user from voting just because they use an outdated SW wallet.
    return address_type not in addresses.ADDRESS_TYPES_PAYMENT


async def _show_cvote_registration(
    keychain: seed.Keychain,
    parameters: messages.CardanoCVoteRegistrationParametersType,
    protocol_magic: int,
    network_id: int,
    should_show_details: bool,
) -> None:
    from .helpers import bech32
    from .helpers.credential import Credential, should_show_credentials

    for delegation in parameters.delegations:
        encoded_public_key = bech32.encode(
            bech32.HRP_CVOTE_PUBLIC_KEY, delegation.vote_public_key
        )
        await layout.confirm_cvote_registration_delegation(
            encoded_public_key, delegation.weight
        )

    if parameters.payment_address:
        show_payment_warning = _should_show_payment_warning(
            addresses.get_type(addresses.get_bytes_unsafe(parameters.payment_address))
        )
        await layout.confirm_cvote_registration_payment_address(
            parameters.payment_address, show_payment_warning
        )
    else:
        address_parameters = parameters.payment_address_parameters
        assert address_parameters  # _validate_cvote_registration_parameters
        show_both_credentials = should_show_credentials(address_parameters)
        show_payment_warning = _should_show_payment_warning(
            address_parameters.address_type
        )
        await layout.show_cvote_registration_payment_credentials(
            Credential.payment_credential(address_parameters),
            Credential.stake_credential(address_parameters),
            show_both_credentials,
            show_payment_warning,
        )

    encoded_public_key: str | None = None
    if parameters.vote_public_key:
        encoded_public_key = bech32.encode(
            bech32.HRP_CVOTE_PUBLIC_KEY, parameters.vote_public_key
        )

    voting_purpose: int | None = (
        _get_voting_purpose_to_serialize(parameters) if should_show_details else None
    )

    await layout.confirm_cvote_registration(
        encoded_public_key,
        parameters.staking_path,
        parameters.nonce,
        voting_purpose,
    )


def get_hash_and_supplement(
    keychain: seed.Keychain,
    auxiliary_data: messages.CardanoTxAuxiliaryData,
    protocol_magic: int,
    network_id: int,
) -> tuple[bytes, messages.CardanoTxAuxiliaryDataSupplement]:
    from trezor import messages
    from trezor.enums import CardanoTxAuxiliaryDataSupplementType

    if parameters := auxiliary_data.cvote_registration_parameters:
        (
            cvote_registration_payload,
            cvote_registration_signature,
        ) = _get_signed_cvote_registration_payload(
            keychain, parameters, protocol_magic, network_id
        )
        auxiliary_data_hash = _get_cvote_registration_hash(
            cvote_registration_payload, cvote_registration_signature
        )
        auxiliary_data_supplement = messages.CardanoTxAuxiliaryDataSupplement(
            type=CardanoTxAuxiliaryDataSupplementType.CVOTE_REGISTRATION_SIGNATURE,
            auxiliary_data_hash=auxiliary_data_hash,
            cvote_registration_signature=cvote_registration_signature,
        )
        return auxiliary_data_hash, auxiliary_data_supplement
    else:
        assert auxiliary_data.hash is not None  # validate_auxiliary_data
        return auxiliary_data.hash, messages.CardanoTxAuxiliaryDataSupplement(
            type=CardanoTxAuxiliaryDataSupplementType.NONE
        )


def _get_cvote_registration_hash(
    cvote_registration_payload: CVoteRegistrationPayload,
    cvote_registration_payload_signature: bytes,
) -> bytes:
    # _cborize_catalyst_registration
    cvote_registration_signature = {1: cvote_registration_payload_signature}
    cborized_catalyst_registration = {
        _METADATA_KEY_CVOTE_REGISTRATION: cvote_registration_payload,
        _METADATA_KEY_CVOTE_REGISTRATION_SIGNATURE: cvote_registration_signature,
    }

    # _get_hash
    # _wrap_metadata
    # A new structure of metadata is used after Cardano Mary era. The metadata
    # is wrapped in a tuple and auxiliary_scripts may follow it. Cardano
    # tooling uses this new format of "wrapped" metadata even if no
    # auxiliary_scripts are included. So we do the same here.
    # https://github.com/input-output-hk/cardano-ledger-specs/blob/f7deb22be14d31b535f56edc3ca542c548244c67/shelley-ma/shelley-ma-test/cddl-files/shelley-ma.cddl#L212
    metadata = (cborized_catalyst_registration, ())
    auxiliary_data = cbor.encode(metadata)
    return hashlib.blake2b(
        data=auxiliary_data, outlen=_AUXILIARY_DATA_HASH_SIZE
    ).digest()


def _get_signed_cvote_registration_payload(
    keychain: seed.Keychain,
    parameters: messages.CardanoCVoteRegistrationParametersType,
    protocol_magic: int,
    network_id: int,
) -> SignedCVoteRegistrationPayload:
    delegations_or_key: Delegations | bytes
    if len(parameters.delegations) > 0:
        delegations_or_key = [
            (delegation.vote_public_key, delegation.weight)
            for delegation in parameters.delegations
        ]
    elif parameters.vote_public_key:
        delegations_or_key = parameters.vote_public_key
    else:
        raise RuntimeError  # should not be reached - _validate_cvote_registration_parameters

    staking_key = derive_public_key(keychain, parameters.staking_path)

    if parameters.payment_address:
        payment_address = addresses.get_bytes_unsafe(parameters.payment_address)
    else:
        address_parameters = parameters.payment_address_parameters
        assert address_parameters  # _validate_cvote_registration_parameters
        payment_address = addresses.derive_bytes(
            keychain,
            address_parameters,
            protocol_magic,
            network_id,
        )

    voting_purpose = _get_voting_purpose_to_serialize(parameters)

    payload: CVoteRegistrationPayload = {
        1: delegations_or_key,
        2: staking_key,
        3: payment_address,
        4: parameters.nonce,
    }
    if voting_purpose is not None:
        payload[5] = voting_purpose

    signature = _create_cvote_registration_payload_signature(
        keychain,
        payload,
        parameters.staking_path,
    )

    return payload, signature


def _create_cvote_registration_payload_signature(
    keychain: seed.Keychain,
    cvote_registration_payload: CVoteRegistrationPayload,
    path: list[int],
) -> bytes:
    from trezor.crypto.curve import ed25519

    node = keychain.derive(path)

    encoded_cvote_registration = cbor.encode(
        {_METADATA_KEY_CVOTE_REGISTRATION: cvote_registration_payload}
    )

    cvote_registration_hash = hashlib.blake2b(
        data=encoded_cvote_registration,
        outlen=_CVOTE_REGISTRATION_HASH_SIZE,
    ).digest()

    return ed25519.sign_ext(
        node.private_key(), node.private_key_ext(), cvote_registration_hash
    )
