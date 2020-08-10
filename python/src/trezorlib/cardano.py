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

from typing import List

from . import messages, tools
from .tools import expect

PROTOCOL_MAGICS = {"mainnet": 764824073, "testnet": 42}
NETWORK_IDS = {"mainnet": 1, "testnet": 0}

REQUIRED_FIELDS_TRANSACTION = ("inputs", "outputs")
REQUIRED_FIELDS_INPUT = ("path", "prev_hash", "prev_index")
REQUIRED_FIELDS_CERTIFICATE = ("path", "type")
REQUIRED_FIELDS_WITHDRAWAL = ("path", "amount")

INCOMPLETE_OUTPUT_ERROR_MESSAGE = "The output is missing some fields"

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
        certificate_pointer = create_certificate_pointer(
            block_index, tx_index, certificate_index
        )

    return messages.CardanoAddressParametersType(
        address_type=address_type,
        address_n=address_n,
        address_n_staking=address_n_staking,
        staking_key_hash=staking_key_hash,
        certificate_pointer=certificate_pointer,
    )


def create_certificate_pointer(
    block_index: int, tx_index: int, certificate_index: int
) -> messages.CardanoBlockchainPointerType:
    if block_index is None or tx_index is None or certificate_index is None:
        raise ValueError("Invalid pointer parameters")

    return messages.CardanoBlockchainPointerType(
        block_index=block_index, tx_index=tx_index, certificate_index=certificate_index
    )


def create_input(input) -> messages.CardanoTxInputType:
    if not all(k in input for k in REQUIRED_FIELDS_INPUT):
        raise ValueError("The input is missing some fields")

    path = input["path"]

    return messages.CardanoTxInputType(
        address_n=tools.parse_path(path),
        prev_hash=bytes.fromhex(input["prev_hash"]),
        prev_index=input["prev_index"],
    )


def create_output(output) -> messages.CardanoTxOutputType:
    contains_address = "address" in output
    contains_address_type = "addressType" in output

    if "amount" not in output:
        raise ValueError(INCOMPLETE_OUTPUT_ERROR_MESSAGE)
    if not (contains_address or contains_address_type):
        raise ValueError(INCOMPLETE_OUTPUT_ERROR_MESSAGE)

    if contains_address:
        return messages.CardanoTxOutputType(
            address=output["address"], amount=int(output["amount"])
        )
    else:
        return _create_change_output(output)


def _create_change_output(output) -> messages.CardanoTxOutputType:
    if "path" not in output:
        raise ValueError(INCOMPLETE_OUTPUT_ERROR_MESSAGE)

    staking_key_hash_bytes = None
    if "stakingKeyHash" in output:
        staking_key_hash_bytes = bytes.fromhex(output.get("stakingKeyHash"))

    address_parameters = create_address_parameters(
        int(output["addressType"]),
        tools.parse_path(output["path"]),
        tools.parse_path(output.get("stakingPath")),
        staking_key_hash_bytes,
        output.get("blockIndex"),
        output.get("txIndex"),
        output.get("certificateIndex"),
    )

    return messages.CardanoTxOutputType(
        address_parameters=address_parameters, amount=int(output["amount"])
    )


def create_certificate(certificate) -> messages.CardanoTxCertificateType:
    if not all(k in certificate for k in REQUIRED_FIELDS_CERTIFICATE):
        raise ValueError("The certificate is missing some fields")

    path = certificate["path"]
    certificate_type = certificate["type"]

    if certificate_type == messages.CardanoCertificateType.STAKE_DELEGATION:
        if "pool" not in certificate:
            raise ValueError("The certificate is missing some fields")

        pool = certificate["pool"]
        return messages.CardanoTxCertificateType(
            type=certificate_type,
            path=tools.parse_path(path),
            pool=bytes.fromhex(pool),
        )
    elif (
        certificate_type == messages.CardanoCertificateType.STAKE_REGISTRATION
        or certificate_type == messages.CardanoCertificateType.STAKE_DEREGISTRATION
    ):
        return messages.CardanoTxCertificateType(
            type=certificate_type, path=tools.parse_path(path),
        )
    else:
        raise ValueError("Unknown certificate type")


def create_withdrawal(withdrawal) -> messages.CardanoTxWithdrawalType:
    if not all(k in withdrawal for k in REQUIRED_FIELDS_WITHDRAWAL):
        raise ValueError("Withdrawal is missing some fields")

    path = withdrawal["path"]
    return messages.CardanoTxWithdrawalType(
        path=tools.parse_path(path), amount=int(withdrawal["amount"]),
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
    ttl: int,
    certificates: List[messages.CardanoTxCertificateType] = (),
    withdrawals: List[messages.CardanoTxWithdrawalType] = (),
    metadata: bytes = None,
    protocol_magic: int = PROTOCOL_MAGICS["mainnet"],
    network_id: int = NETWORK_IDS["mainnet"],
) -> messages.CardanoSignedTx:
    response = client.call(
        messages.CardanoSignTx(
            inputs=inputs,
            outputs=outputs,
            fee=fee,
            ttl=ttl,
            certificates=certificates,
            withdrawals=withdrawals,
            metadata=metadata,
            protocol_magic=protocol_magic,
            network_id=network_id,
        )
    )

    return response
