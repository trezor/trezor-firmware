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

INCOMPLETE_OUTPUT_ERROR_MESSAGE = "The output is missing some fields"


def create_address_parameters(
    address_type: messages.CardanoAddressType,
    spending_key_path_str: str,
    staking_key_path_str: str = None,
    staking_key_hash_str: str = None,
    block_index: int = None,
    tx_index: int = None,
    certificate_index: int = None,
) -> messages.CardanoAddressParametersType:
    staking_key_path = None
    staking_key_hash = None
    certificate_pointer = None

    if not _is_known_address_type(address_type):
        raise ValueError("Unknown address type")

    if address_type == messages.CardanoAddressType.BASE:
        if staking_key_path_str:
            staking_key_path = tools.parse_path(staking_key_path_str)
        elif staking_key_hash_str:
            staking_key_hash = bytes.fromhex(staking_key_hash_str)
        else:
            raise ValueError(
                "Base address requires a staking key path or a staking key hash"
            )
    elif address_type == messages.CardanoAddressType.POINTER:
        certificate_pointer = create_certificate_pointer(
            block_index, tx_index, certificate_index
        )

    return messages.CardanoAddressParametersType(
        address_type=address_type,
        spending_key_path=tools.parse_path(spending_key_path_str),
        staking_key_path=staking_key_path,
        staking_key_hash=staking_key_hash,
        certificate_pointer=certificate_pointer,
    )


def _is_known_address_type(address_type: messages.CardanoAddressType) -> bool:
    return (
        address_type == messages.CardanoAddressType.BYRON
        or address_type == messages.CardanoAddressType.BASE
        or address_type == messages.CardanoAddressType.POINTER
        or address_type == messages.CardanoAddressType.ENTERPRISE
        or address_type == messages.CardanoAddressType.REWARD
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
    if not all(input.get(k) is not None for k in REQUIRED_FIELDS_INPUT):
        raise ValueError("The input is missing some fields")

    path = input["path"]

    return messages.CardanoTxInputType(
        address_n=tools.parse_path(path),
        prev_hash=bytes.fromhex(input["prev_hash"]),
        prev_index=input["prev_index"],
    )


def create_output(output) -> messages.CardanoTxOutputType:
    contains_address = output.get("address") is not None
    contains_address_type = output.get("addressType") is not None

    if output.get("amount") is None:
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
    if output.get("path") is None:
        raise ValueError(INCOMPLETE_OUTPUT_ERROR_MESSAGE)

    address_parameters = create_address_parameters(
        int(output["addressType"]),
        output["path"],
        output.get("stakingKeyPath"),
        output.get("stakingKeyHash"),
        output.get("blockIndex"),
        output.get("txIndex"),
        output.get("certificateIndex"),
    )

    return messages.CardanoTxOutputType(
        address_parameters=address_parameters, amount=int(output["amount"])
    )


# ====== Client functions ====== #


@expect(messages.CardanoAddress, field="address")
def get_address(
    client,
    address_parameters: messages.CardanoAddressParametersType,
    protocol_magic: int,
    network_id: int,
    show_display=False,
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
    protocol_magic: int,
    network_id: int,
) -> messages.CardanoSignedTx:
    response = client.call(
        messages.CardanoSignTx(
            inputs=inputs,
            outputs=outputs,
            fee=fee,
            ttl=ttl,
            protocol_magic=protocol_magic,
            network_id=network_id,
        )
    )

    return response
