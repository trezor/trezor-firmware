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

REQUIRED_FIELDS_TRANSACTION = ("inputs", "outputs")
REQUIRED_FIELDS_INPUT = ("path", "prev_hash", "prev_index")


@expect(messages.CardanoAddress, field="address")
def get_address(
    client, address_n: List[int], protocol_magic: int, show_display=False
) -> messages.CardanoAddress:
    return client.call(
        messages.CardanoGetAddress(
            address_n=address_n,
            protocol_magic=protocol_magic,
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
) -> messages.CardanoSignedTx:
    response = client.call(
        messages.CardanoSignTx(
            inputs=inputs,
            outputs=outputs,
            fee=fee,
            ttl=ttl,
            protocol_magic=protocol_magic,
        )
    )

    return response


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
    if not output.get("amount") or not (output.get("address") or output.get("path")):
        raise ValueError("The output is missing some fields")

    if output.get("path"):
        path = output["path"]

        return messages.CardanoTxOutputType(
            address_n=tools.parse_path(path), amount=int(output["amount"])
        )

    return messages.CardanoTxOutputType(
        address=output["address"], amount=int(output["amount"])
    )
