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
from typing import List, Optional

from . import exceptions, messages, tools
from .tools import expect

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


def parse_input(tx_input) -> messages.CardanoTxInputType:
    if not all(k in tx_input for k in REQUIRED_FIELDS_INPUT):
        raise ValueError("The input is missing some fields")

    return messages.CardanoTxInputType(
        address_n=tools.parse_path(tx_input.get("path")),
        prev_hash=bytes.fromhex(tx_input["prev_hash"]),
        prev_index=tx_input["prev_index"],
    )


def parse_output(output) -> messages.CardanoTxOutputType:
    contains_address = "address" in output
    contains_address_type = "addressType" in output

    if "amount" not in output:
        raise ValueError(INCOMPLETE_OUTPUT_ERROR_MESSAGE)
    if not (contains_address or contains_address_type):
        raise ValueError(INCOMPLETE_OUTPUT_ERROR_MESSAGE)

    address = None
    address_parameters = None
    token_bundle = None

    if contains_address:
        address = output["address"]

    if contains_address_type:
        address_parameters = _parse_address_parameters(output)

    if "token_bundle" in output:
        token_bundle = _parse_token_bundle(output["token_bundle"])

    return messages.CardanoTxOutputType(
        address=address,
        address_parameters=address_parameters,
        amount=int(output["amount"]),
        token_bundle=token_bundle,
    )


def _parse_token_bundle(token_bundle) -> List[messages.CardanoAssetGroupType]:
    result = []
    for token_group in token_bundle:
        if not all(k in token_group for k in REQUIRED_FIELDS_TOKEN_GROUP):
            raise ValueError(INVALID_OUTPUT_TOKEN_BUNDLE_ENTRY)

        result.append(
            messages.CardanoAssetGroupType(
                policy_id=bytes.fromhex(token_group["policy_id"]),
                tokens=_parse_tokens(token_group["tokens"]),
            )
        )

    return result


def _parse_tokens(tokens) -> List[messages.CardanoTokenType]:
    result = []
    for token in tokens:
        if not all(k in token for k in REQUIRED_FIELDS_TOKEN):
            raise ValueError(INVALID_OUTPUT_TOKEN_BUNDLE_ENTRY)

        result.append(
            messages.CardanoTokenType(
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


def parse_certificate(certificate) -> messages.CardanoTxCertificateType:
    CERTIFICATE_MISSING_FIELDS_ERROR = ValueError(
        "The certificate is missing some fields"
    )

    if not all(k in certificate for k in REQUIRED_FIELDS_CERTIFICATE):
        raise CERTIFICATE_MISSING_FIELDS_ERROR

    certificate_type = certificate["type"]

    if certificate_type == messages.CardanoCertificateType.STAKE_DELEGATION:
        if "pool" not in certificate:
            raise CERTIFICATE_MISSING_FIELDS_ERROR

        return messages.CardanoTxCertificateType(
            type=certificate_type,
            path=tools.parse_path(certificate["path"]),
            pool=bytes.fromhex(certificate["pool"]),
        )
    elif certificate_type in (
        messages.CardanoCertificateType.STAKE_REGISTRATION,
        messages.CardanoCertificateType.STAKE_DEREGISTRATION,
    ):
        if "path" not in certificate:
            raise CERTIFICATE_MISSING_FIELDS_ERROR
        return messages.CardanoTxCertificateType(
            type=certificate_type,
            path=tools.parse_path(certificate["path"]),
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

        return messages.CardanoTxCertificateType(
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
                owners=[
                    _parse_pool_owner(pool_owner)
                    for pool_owner in pool_parameters.get("owners", [])
                ],
                relays=[
                    _parse_pool_relay(pool_relay)
                    for pool_relay in pool_parameters.get("relays", [])
                ]
                if "relays" in pool_parameters
                else [],
            ),
        )
    else:
        raise ValueError("Unknown certificate type")


def _parse_pool_owner(pool_owner) -> messages.CardanoPoolOwnerType:
    if "staking_key_path" in pool_owner:
        return messages.CardanoPoolOwnerType(
            staking_key_path=tools.parse_path(pool_owner["staking_key_path"])
        )

    return messages.CardanoPoolOwnerType(
        staking_key_hash=bytes.fromhex(pool_owner["staking_key_hash"])
    )


def _parse_pool_relay(pool_relay) -> messages.CardanoPoolRelayParametersType:
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

        return messages.CardanoPoolRelayParametersType(
            type=pool_relay_type,
            port=int(pool_relay["port"]),
            ipv4_address=ipv4_address_packed,
            ipv6_address=ipv6_address_packed,
        )
    elif pool_relay_type == messages.CardanoPoolRelayType.SINGLE_HOST_NAME:
        return messages.CardanoPoolRelayParametersType(
            type=pool_relay_type,
            port=int(pool_relay["port"]),
            host_name=pool_relay["host_name"],
        )
    elif pool_relay_type == messages.CardanoPoolRelayType.MULTIPLE_HOST_NAME:
        return messages.CardanoPoolRelayParametersType(
            type=pool_relay_type,
            host_name=pool_relay["host_name"],
        )

    raise ValueError("Unknown pool relay type")


def parse_withdrawal(withdrawal) -> messages.CardanoTxWithdrawalType:
    if not all(k in withdrawal for k in REQUIRED_FIELDS_WITHDRAWAL):
        raise ValueError("Withdrawal is missing some fields")

    path = withdrawal["path"]
    return messages.CardanoTxWithdrawalType(
        path=tools.parse_path(path),
        amount=int(withdrawal["amount"]),
    )


def parse_auxiliary_data(auxiliary_data) -> messages.CardanoTxAuxiliaryDataType:
    if auxiliary_data is None:
        return None

    AUXILIARY_DATA_MISSING_FIELDS_ERROR = ValueError(
        "Auxiliary data is missing some fields"
    )

    # include all provided fields so we can test validation in FW
    blob = None
    if "blob" in auxiliary_data:
        blob = bytes.fromhex(auxiliary_data["blob"])

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

    if blob is None and catalyst_registration_parameters is None:
        raise AUXILIARY_DATA_MISSING_FIELDS_ERROR

    return messages.CardanoTxAuxiliaryDataType(
        blob=blob,
        catalyst_registration_parameters=catalyst_registration_parameters,
    )


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


@expect(messages.CardanoSignedTx)
def sign_tx(
    client,
    inputs: List[messages.CardanoTxInputType],
    outputs: List[messages.CardanoTxOutputType],
    fee: int,
    ttl: Optional[int],
    validity_interval_start: Optional[int],
    certificates: List[messages.CardanoTxCertificateType] = (),
    withdrawals: List[messages.CardanoTxWithdrawalType] = (),
    protocol_magic: int = PROTOCOL_MAGICS["mainnet"],
    network_id: int = NETWORK_IDS["mainnet"],
    auxiliary_data: messages.CardanoTxAuxiliaryDataType = None,
) -> messages.CardanoSignedTx:
    response = client.call(
        messages.CardanoSignTx(
            inputs=inputs,
            outputs=outputs,
            fee=fee,
            ttl=ttl,
            validity_interval_start=validity_interval_start,
            certificates=certificates,
            withdrawals=withdrawals,
            protocol_magic=protocol_magic,
            network_id=network_id,
            auxiliary_data=auxiliary_data,
        )
    )

    result = bytearray()
    while isinstance(response, messages.CardanoSignedTxChunk):
        result.extend(response.signed_tx_chunk)
        response = client.call(messages.CardanoSignedTxChunkAck())

    if not isinstance(response, messages.CardanoSignedTx):
        raise exceptions.TrezorException("Unexpected response")

    if response.serialized_tx is not None:
        result.extend(response.serialized_tx)

    return messages.CardanoSignedTx(tx_hash=response.tx_hash, serialized_tx=result)
