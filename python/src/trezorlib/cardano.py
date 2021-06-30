# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

from ipaddress import ip_address
from itertools import chain
from typing import Dict, Iterator, List, Optional, Tuple, Union

from . import exceptions, messages, tools
from .tools import expect

SIGNING_MODE_IDS = {
    "ORDINARY_TRANSACTION": messages.CardanoTxSigningMode.ORDINARY_TRANSACTION,
    "POOL_REGISTRATION_AS_OWNER": messages.CardanoTxSigningMode.POOL_REGISTRATION_AS_OWNER,
}

PROTOCOL_MAGICS = {"mainnet": 764824073, "testnet": 42}
NETWORK_IDS = {"mainnet": 1, "testnet": 0}

REQUIRED_FIELDS_TRANSACTION = ("inputs", "outputs")
REQUIRED_FIELDS_INPUT = ("prev_hash", "prev_index")
REQUIRED_FIELDS_CERTIFICATE = ("type",)
REQUIRED_FIELDS_POOL_PARAMETERS = (
    "pool_id",
    "vrf_key_hash",
    "pledge",
    "cost",
    "margin",
    "reward_account",
    "owners",
)
REQUIRED_FIELDS_WITHDRAWAL = ("path", "amount")
REQUIRED_FIELDS_TOKEN_GROUP = ("policy_id", "tokens")
REQUIRED_FIELDS_TOKEN = ("asset_name_bytes", "amount")
REQUIRED_FIELDS_CATALYST_REGISTRATION = (
    "voting_public_key",
    "staking_path",
    "nonce",
    "reward_address_parameters",
)

INCOMPLETE_OUTPUT_ERROR_MESSAGE = "The output is missing some fields"

INVALID_OUTPUT_TOKEN_BUNDLE_ENTRY = "The output's token_bundle entry is invalid"

ADDRESS_TYPES = (
    messages.CardanoAddressType.BYRON,
    messages.CardanoAddressType.BASE,
    messages.CardanoAddressType.POINTER,
    messages.CardanoAddressType.ENTERPRISE,
    messages.CardanoAddressType.REWARD,
)

InputWithPath = Tuple[messages.CardanoTxInput, List[int]]
AssetGroupWithTokens = Tuple[messages.CardanoAssetGroup, List[messages.CardanoToken]]
OutputWithAssetGroups = Tuple[messages.CardanoTxOutput, List[AssetGroupWithTokens]]
OutputItem = Union[
    messages.CardanoTxOutput, messages.CardanoAssetGroup, messages.CardanoToken
]
CertificateItem = Union[
    messages.CardanoTxCertificate,
    messages.CardanoPoolOwner,
    messages.CardanoPoolRelayParameters,
]
PoolOwnersAndRelays = Tuple[
    List[messages.CardanoPoolOwner], List[messages.CardanoPoolRelayParameters]
]
CertificateWithPoolOwnersAndRelays = Tuple[
    messages.CardanoTxCertificate, Optional[PoolOwnersAndRelays]
]
Path = List[int]
Witness = Tuple[Path, bytes]
AuxiliaryDataSupplement = Dict[str, Union[int, bytes]]
SignTxResponse = Dict[str, Union[bytes, List[Witness], AuxiliaryDataSupplement]]


def create_address_parameters(
    address_type: messages.CardanoAddressType,
    address_n: List[int],
    address_n_staking: List[int] = None,
    staking_key_hash: bytes = None,
    block_index: int = None,
    tx_index: int = None,
    certificate_index: int = None,
) -> messages.CardanoAddressParametersType:
    certificate_pointer = None

    if address_type not in ADDRESS_TYPES:
        raise ValueError("Unknown address type")

    if address_type == messages.CardanoAddressType.POINTER:
        certificate_pointer = _create_certificate_pointer(
            block_index, tx_index, certificate_index
        )

    return messages.CardanoAddressParametersType(
        address_type=address_type,
        address_n=address_n,
        address_n_staking=address_n_staking,
        staking_key_hash=staking_key_hash,
        certificate_pointer=certificate_pointer,
    )


def _create_certificate_pointer(
    block_index: int, tx_index: int, certificate_index: int
) -> messages.CardanoBlockchainPointerType:
    if block_index is None or tx_index is None or certificate_index is None:
        raise ValueError("Invalid pointer parameters")

    return messages.CardanoBlockchainPointerType(
        block_index=block_index, tx_index=tx_index, certificate_index=certificate_index
    )


def parse_input(tx_input) -> InputWithPath:
    if not all(k in tx_input for k in REQUIRED_FIELDS_INPUT):
        raise ValueError("The input is missing some fields")

    path = tools.parse_path(tx_input.get("path"))
    return (
        messages.CardanoTxInput(
            prev_hash=bytes.fromhex(tx_input["prev_hash"]),
            prev_index=tx_input["prev_index"],
        ),
        path,
    )


def parse_output(output) -> OutputWithAssetGroups:
    contains_address = "address" in output
    contains_address_type = "addressType" in output

    if "amount" not in output:
        raise ValueError(INCOMPLETE_OUTPUT_ERROR_MESSAGE)
    if not (contains_address or contains_address_type):
        raise ValueError(INCOMPLETE_OUTPUT_ERROR_MESSAGE)

    address = None
    address_parameters = None
    token_bundle = []

    if contains_address:
        address = output["address"]

    if contains_address_type:
        address_parameters = _parse_address_parameters(output)

    if "token_bundle" in output:
        token_bundle = _parse_token_bundle(output["token_bundle"])

    return (
        messages.CardanoTxOutput(
            address=address,
            address_parameters=address_parameters,
            amount=int(output["amount"]),
            asset_groups_count=len(token_bundle),
        ),
        token_bundle,
    )


def _parse_token_bundle(token_bundle) -> List[AssetGroupWithTokens]:
    result = []
    for token_group in token_bundle:
        if not all(k in token_group for k in REQUIRED_FIELDS_TOKEN_GROUP):
            raise ValueError(INVALID_OUTPUT_TOKEN_BUNDLE_ENTRY)

        tokens = _parse_tokens(token_group["tokens"])

        result.append(
            (
                messages.CardanoAssetGroup(
                    policy_id=bytes.fromhex(token_group["policy_id"]),
                    tokens_count=len(tokens),
                ),
                tokens,
            )
        )

    return result


def _parse_tokens(tokens) -> List[messages.CardanoToken]:
    result = []
    for token in tokens:
        if not all(k in token for k in REQUIRED_FIELDS_TOKEN):
            raise ValueError(INVALID_OUTPUT_TOKEN_BUNDLE_ENTRY)

        result.append(
            messages.CardanoToken(
                asset_name_bytes=bytes.fromhex(token["asset_name_bytes"]),
                amount=int(token["amount"]),
            )
        )

    return result


def _parse_address_parameters(
    address_parameters,
) -> messages.CardanoAddressParametersType:
    if "path" not in address_parameters:
        raise ValueError(INCOMPLETE_OUTPUT_ERROR_MESSAGE)

    staking_key_hash_bytes = None
    if "stakingKeyHash" in address_parameters:
        staking_key_hash_bytes = bytes.fromhex(address_parameters.get("stakingKeyHash"))

    return create_address_parameters(
        int(address_parameters["addressType"]),
        tools.parse_path(address_parameters["path"]),
        tools.parse_path(address_parameters.get("stakingPath")),
        staking_key_hash_bytes,
        address_parameters.get("blockIndex"),
        address_parameters.get("txIndex"),
        address_parameters.get("certificateIndex"),
    )


def parse_certificate(certificate) -> CertificateWithPoolOwnersAndRelays:
    CERTIFICATE_MISSING_FIELDS_ERROR = ValueError(
        "The certificate is missing some fields"
    )

    if not all(k in certificate for k in REQUIRED_FIELDS_CERTIFICATE):
        raise CERTIFICATE_MISSING_FIELDS_ERROR

    certificate_type = certificate["type"]

    if certificate_type == messages.CardanoCertificateType.STAKE_DELEGATION:
        if "pool" not in certificate:
            raise CERTIFICATE_MISSING_FIELDS_ERROR

        return (
            messages.CardanoTxCertificate(
                type=certificate_type,
                path=tools.parse_path(certificate["path"]),
                pool=bytes.fromhex(certificate["pool"]),
            ),
            None,
        )
    elif certificate_type in (
        messages.CardanoCertificateType.STAKE_REGISTRATION,
        messages.CardanoCertificateType.STAKE_DEREGISTRATION,
    ):
        if "path" not in certificate:
            raise CERTIFICATE_MISSING_FIELDS_ERROR
        return (
            messages.CardanoTxCertificate(
                type=certificate_type,
                path=tools.parse_path(certificate["path"]),
            ),
            None,
        )
    elif certificate_type == messages.CardanoCertificateType.STAKE_POOL_REGISTRATION:
        pool_parameters = certificate["pool_parameters"]

        if any(
            required_param not in pool_parameters
            for required_param in REQUIRED_FIELDS_POOL_PARAMETERS
        ):
            raise CERTIFICATE_MISSING_FIELDS_ERROR

        if pool_parameters.get("metadata") is not None:
            pool_metadata = messages.CardanoPoolMetadataType(
                url=pool_parameters["metadata"]["url"],
                hash=bytes.fromhex(pool_parameters["metadata"]["hash"]),
            )
        else:
            pool_metadata = None

        owners = [
            _parse_pool_owner(pool_owner)
            for pool_owner in pool_parameters.get("owners", [])
        ]
        relays = [
            _parse_pool_relay(pool_relay)
            for pool_relay in pool_parameters.get("relays", [])
        ]

        return (
            messages.CardanoTxCertificate(
                type=certificate_type,
                pool_parameters=messages.CardanoPoolParametersType(
                    pool_id=bytes.fromhex(pool_parameters["pool_id"]),
                    vrf_key_hash=bytes.fromhex(pool_parameters["vrf_key_hash"]),
                    pledge=int(pool_parameters["pledge"]),
                    cost=int(pool_parameters["cost"]),
                    margin_numerator=int(pool_parameters["margin"]["numerator"]),
                    margin_denominator=int(pool_parameters["margin"]["denominator"]),
                    reward_account=pool_parameters["reward_account"],
                    metadata=pool_metadata,
                    owners_count=len(owners),
                    relays_count=len(relays),
                ),
            ),
            (owners, relays),
        )
    else:
        raise ValueError("Unknown certificate type")


def _parse_pool_owner(pool_owner) -> messages.CardanoPoolOwner:
    if "staking_key_path" in pool_owner:
        return messages.CardanoPoolOwner(
            staking_key_path=tools.parse_path(pool_owner["staking_key_path"])
        )

    return messages.CardanoPoolOwner(
        staking_key_hash=bytes.fromhex(pool_owner["staking_key_hash"])
    )


def _parse_pool_relay(pool_relay) -> messages.CardanoPoolRelayParameters:
    pool_relay_type = int(pool_relay["type"])

    if pool_relay_type == messages.CardanoPoolRelayType.SINGLE_HOST_IP:
        ipv4_address_packed = (
            ip_address(pool_relay["ipv4_address"]).packed
            if "ipv4_address" in pool_relay
            else None
        )
        ipv6_address_packed = (
            ip_address(pool_relay["ipv6_address"]).packed
            if "ipv6_address" in pool_relay
            else None
        )

        return messages.CardanoPoolRelayParameters(
            type=pool_relay_type,
            port=int(pool_relay["port"]),
            ipv4_address=ipv4_address_packed,
            ipv6_address=ipv6_address_packed,
        )
    elif pool_relay_type == messages.CardanoPoolRelayType.SINGLE_HOST_NAME:
        return messages.CardanoPoolRelayParameters(
            type=pool_relay_type,
            port=int(pool_relay["port"]),
            host_name=pool_relay["host_name"],
        )
    elif pool_relay_type == messages.CardanoPoolRelayType.MULTIPLE_HOST_NAME:
        return messages.CardanoPoolRelayParameters(
            type=pool_relay_type,
            host_name=pool_relay["host_name"],
        )

    raise ValueError("Unknown pool relay type")


def parse_withdrawal(withdrawal) -> messages.CardanoTxWithdrawal:
    if not all(k in withdrawal for k in REQUIRED_FIELDS_WITHDRAWAL):
        raise ValueError("Withdrawal is missing some fields")

    path = withdrawal["path"]
    return messages.CardanoTxWithdrawal(
        path=tools.parse_path(path),
        amount=int(withdrawal["amount"]),
    )


def parse_auxiliary_data(auxiliary_data) -> messages.CardanoTxAuxiliaryData:
    if auxiliary_data is None:
        return None

    AUXILIARY_DATA_MISSING_FIELDS_ERROR = ValueError(
        "Auxiliary data is missing some fields"
    )

    # include all provided fields so we can test validation in FW
    hash = None
    if "hash" in auxiliary_data:
        hash = bytes.fromhex(auxiliary_data["hash"])

    catalyst_registration_parameters = None
    if "catalyst_registration_parameters" in auxiliary_data:
        catalyst_registration = auxiliary_data["catalyst_registration_parameters"]
        if not all(
            k in catalyst_registration for k in REQUIRED_FIELDS_CATALYST_REGISTRATION
        ):
            raise AUXILIARY_DATA_MISSING_FIELDS_ERROR

        catalyst_registration_parameters = (
            messages.CardanoCatalystRegistrationParametersType(
                voting_public_key=bytes.fromhex(
                    catalyst_registration["voting_public_key"]
                ),
                staking_path=tools.parse_path(catalyst_registration["staking_path"]),
                nonce=catalyst_registration["nonce"],
                reward_address_parameters=_parse_address_parameters(
                    catalyst_registration["reward_address_parameters"]
                ),
            )
        )

    if hash is None and catalyst_registration_parameters is None:
        raise AUXILIARY_DATA_MISSING_FIELDS_ERROR

    return messages.CardanoTxAuxiliaryData(
        hash=hash,
        catalyst_registration_parameters=catalyst_registration_parameters,
    )


def _get_witness_paths(
    inputs: List[InputWithPath],
    certificates: List[CertificateWithPoolOwnersAndRelays],
    withdrawals: List[messages.CardanoTxWithdrawal],
) -> List[Path]:
    paths = set()
    for _, path in inputs:
        if path:
            paths.add(tuple(path))
    for certificate, pool_owners_and_relays in certificates:
        if certificate.type in (
            messages.CardanoCertificateType.STAKE_DEREGISTRATION,
            messages.CardanoCertificateType.STAKE_DELEGATION,
        ):
            paths.add(tuple(certificate.path))
        elif (
            certificate.type == messages.CardanoCertificateType.STAKE_POOL_REGISTRATION
            and pool_owners_and_relays is not None
        ):
            owners, _ = pool_owners_and_relays
            for pool_owner in owners:
                if pool_owner.staking_key_path:
                    paths.add(tuple(pool_owner.staking_key_path))
    for withdrawal in withdrawals:
        paths.add(tuple(withdrawal.path))

    return sorted([list(path) for path in paths])


def _get_input_items(inputs: List[InputWithPath]) -> Iterator[messages.CardanoTxInput]:
    for input, _ in inputs:
        yield input


def _get_output_items(outputs: List[OutputWithAssetGroups]) -> Iterator[OutputItem]:
    for output, asset_groups in outputs:
        yield output
        for asset_group, tokens in asset_groups:
            yield asset_group
            yield from tokens


def _get_certificate_items(
    certificates: List[CertificateWithPoolOwnersAndRelays],
) -> Iterator[CertificateItem]:
    for certificate, pool_owners_and_relays in certificates:
        yield certificate
        if pool_owners_and_relays is not None:
            owners, relays = pool_owners_and_relays
            yield from owners
            yield from relays


# ====== Client functions ====== #


@expect(messages.CardanoAddress, field="address")
def get_address(
    client,
    address_parameters: messages.CardanoAddressParametersType,
    protocol_magic: int = PROTOCOL_MAGICS["mainnet"],
    network_id: int = NETWORK_IDS["mainnet"],
    show_display: bool = False,
) -> messages.CardanoAddress:
    return client.call(
        messages.CardanoGetAddress(
            address_parameters=address_parameters,
            protocol_magic=protocol_magic,
            network_id=network_id,
            show_display=show_display,
        )
    )


@expect(messages.CardanoPublicKey)
def get_public_key(client, address_n: List[int]) -> messages.CardanoPublicKey:
    return client.call(messages.CardanoGetPublicKey(address_n=address_n))


def sign_tx(
    client,
    signing_mode: messages.CardanoTxSigningMode,
    inputs: List[InputWithPath],
    outputs: List[OutputWithAssetGroups],
    fee: int,
    ttl: Optional[int],
    validity_interval_start: Optional[int],
    certificates: List[CertificateWithPoolOwnersAndRelays] = (),
    withdrawals: List[messages.CardanoTxWithdrawal] = (),
    protocol_magic: int = PROTOCOL_MAGICS["mainnet"],
    network_id: int = NETWORK_IDS["mainnet"],
    auxiliary_data: messages.CardanoTxAuxiliaryData = None,
) -> SignTxResponse:
    UNEXPECTED_RESPONSE_ERROR = exceptions.TrezorException("Unexpected response")

    witness_paths = _get_witness_paths(inputs, certificates, withdrawals)

    response = client.call(
        messages.CardanoSignTxInit(
            signing_mode=signing_mode,
            inputs_count=len(inputs),
            outputs_count=len(outputs),
            fee=fee,
            ttl=ttl,
            validity_interval_start=validity_interval_start,
            certificates_count=len(certificates),
            withdrawals_count=len(withdrawals),
            protocol_magic=protocol_magic,
            network_id=network_id,
            has_auxiliary_data=auxiliary_data is not None,
            witness_requests_count=len(witness_paths),
        )
    )
    if not isinstance(response, messages.CardanoTxItemAck):
        raise UNEXPECTED_RESPONSE_ERROR

    for tx_item in chain(
        _get_input_items(inputs),
        _get_output_items(outputs),
        _get_certificate_items(certificates),
        withdrawals,
    ):
        response = client.call(tx_item)
        if not isinstance(response, messages.CardanoTxItemAck):
            raise UNEXPECTED_RESPONSE_ERROR

    sign_tx_response = {}

    if auxiliary_data is not None:
        auxiliary_data_supplement = client.call(auxiliary_data)
        if not isinstance(
            auxiliary_data_supplement, messages.CardanoTxAuxiliaryDataSupplement
        ):
            raise UNEXPECTED_RESPONSE_ERROR
        if (
            auxiliary_data_supplement.type
            != messages.CardanoTxAuxiliaryDataSupplementType.NONE
        ):
            sign_tx_response[
                "auxiliary_data_supplement"
            ] = auxiliary_data_supplement.__dict__

        response = client.call(messages.CardanoTxHostAck())
        if not isinstance(response, messages.CardanoTxItemAck):
            raise UNEXPECTED_RESPONSE_ERROR

    sign_tx_response["witnesses"] = []
    for path in witness_paths:
        response = client.call(messages.CardanoTxWitnessRequest(path=path))
        if not isinstance(response, messages.CardanoTxWitnessResponse):
            raise UNEXPECTED_RESPONSE_ERROR
        sign_tx_response["witnesses"].append(
            {
                "type": response.type,
                "pub_key": response.pub_key,
                "signature": response.signature,
                "chain_code": response.chain_code,
            }
        )

    response = client.call(messages.CardanoTxHostAck())
    if not isinstance(response, messages.CardanoTxBodyHash):
        raise UNEXPECTED_RESPONSE_ERROR
    sign_tx_response["tx_hash"] = response.tx_hash

    response = client.call(messages.CardanoTxHostAck())
    if not isinstance(response, messages.CardanoSignTxFinished):
        raise UNEXPECTED_RESPONSE_ERROR

    return sign_tx_response
