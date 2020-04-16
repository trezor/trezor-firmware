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
from .tools import expect, session

REQUIRED_FIELDS_TRANSACTION = ("inputs", "outputs", "transactions")
REQUIRED_FIELDS_INPUT = ("path", "prev_hash", "prev_index", "type")


@expect(messages.CardanoAddress, field="address")
def get_address(
    client, address_parameters, show_display=False, network_id=0,
):
    return client.call(
        messages.CardanoGetAddress(
            address_parameters=address_parameters,
            show_display=show_display,
            network_id=network_id,
        )
    )


@expect(messages.CardanoPublicKey)
def get_public_key(client, address_n):
    return client.call(messages.CardanoGetPublicKey(address_n=address_n))


# todo: merge with sign_tx
@session
def sign_tx(
    client,
    inputs: List[messages.CardanoTxInputType],
    outputs: List[messages.CardanoTxOutputType],
    fee,
    ttl,
    certificates: List[messages.CardanoTxCertificate],
    protocol_magic,
):
    response = client.call(
        messages.CardanoSignTx(
            inputs=inputs,
            outputs=outputs,
            protocol_magic=protocol_magic,
            fee=fee,
            ttl=ttl,
            certificates=certificates,
        )
    )

    return response


def create_certificate_pointer(
    block_index: int, tx_index: int, certificate_index: int
) -> messages.CardanoCertificatePointerType:
    if block_index is None or tx_index is None or certificate_index is None:
        raise ValueError("Invalid pointer parameters")

    return messages.CardanoCertificatePointerType(
        block_index=block_index, tx_index=tx_index, certificate_index=certificate_index
    )


def create_address_parameters(
    address_type: messages.CardanoAddressType,
    address_n: list,
    certificate_pointer: messages.CardanoCertificatePointerType = None,
    staking_key_hash: bytes = None,
) -> messages.CardanoAddressParametersType:
    return messages.CardanoAddressParametersType(
        address_type=address_type,
        address_n=address_n,
        certificate_pointer=certificate_pointer,
        staking_key_hash=staking_key_hash,
    )


def create_input(input) -> messages.CardanoTxInputType:
    if not all(input.get(k) is not None for k in REQUIRED_FIELDS_INPUT):
        raise ValueError("The input is missing some fields")

    path = input["path"]

    return messages.CardanoTxInputType(
        address_n=tools.parse_path(path),
        prev_hash=bytes.fromhex(input["prev_hash"]),
        prev_index=input["prev_index"],
        type=input["type"],
    )


def create_output(output) -> messages.CardanoTxOutputType:
    if not output.get("amount") or not (
        output.get("address") or (output.get("addressType") is not None)
    ):
        raise ValueError("The output is missing some fields")

    if output.get("addressType") is not None:
        return _create_change_address_output(output)

    return messages.CardanoTxOutputType(
        address=output["address"], amount=int(output["amount"])
    )


def _create_change_address_output(output) -> messages.CardanoTxOutputType:
    address_type = int(output["addressType"])
    if address_type == messages.CardanoAddressType.BASE_ADDRESS:
        if not output.get("path"):
            raise ValueError("The output is missing some fields")

        path = output["path"]
        if output.get("stakingKeyHash"):
            staking_key_hash = bytes.fromhex(output["stakingKeyHash"])
        else:
            staking_key_hash = None

        return messages.CardanoTxOutputType(
            address_parameters=messages.CardanoAddressParametersType(
                address_type=address_type,
                address_n=tools.parse_path(path),
                staking_key_hash=staking_key_hash,
            ),
            amount=int(output["amount"]),
        )
    elif address_type == messages.CardanoAddressType.POINTER_ADDRESS:
        if not output.get("path") or not output.get("pointer"):
            raise ValueError("The output is missing some fields")

        path = output["path"]

        pointer = output["pointer"]
        # todo: GK - validate pointer function? or use create_pointer but check validation
        if (
            not pointer.get("block_index")
            or not pointer.get("tx_index")
            or not pointer.get("certificate_index")
        ):
            raise ValueError("The output is missing some fields")

        return messages.CardanoTxOutputType(
            address_parameters=messages.CardanoAddressParametersType(
                address_type=address_type,
                address_n=tools.parse_path(path),
                certificate_pointer=messages.CardanoCertificatePointerType(
                    block_index=pointer["block_index"],
                    tx_index=pointer["tx_index"],
                    certificate_index=pointer["certificate_index"],
                ),
            ),
            amount=int(output["amount"]),
        )
    elif address_type == messages.CardanoAddressType.ENTERPRISE_ADDRESS:
        if not output.get("path"):
            raise ValueError("The output is missing some fields")

        path = output["path"]

        return messages.CardanoTxOutputType(
            address_parameters=messages.CardanoAddressParametersType(
                address_type=address_type, address_n=tools.parse_path(path),
            ),
            amount=int(output["amount"]),
        )
    elif address_type == messages.CardanoAddressType.BOOTSTRAP_ADDRESS:
        if not output.get("path"):
            raise ValueError("The output is missing some fields")

        path = output["path"]
        return messages.CardanoTxOutputType(
            address_n=tools.parse_path(path), amount=int(output["amount"])
        )

    raise ValueError("Unknown address type")


def create_certificate(certificate) -> messages.CardanoTxCertificate:
    # todo: some validation, checks
    # todo: other certificates
    path = certificate["path"]
    if certificate.get("pool"):
        pool = certificate["pool"]
        # todo: refactor
        return messages.CardanoTxCertificate(
            type=certificate["type"], path=tools.parse_path(path), pool=pool
        )

    return messages.CardanoTxCertificate(
        type=certificate["type"], path=tools.parse_path(path),
    )
