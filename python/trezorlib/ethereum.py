# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
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

from . import messages as proto
from .tools import CallException, expect, normalize_nfc, session

import json


def int_to_big_endian(value):
    return value.to_bytes((value.bit_length() + 7) // 8, "big")


# ====== Client functions ====== #


@expect(proto.EthereumAddress, field="address")
def get_address(client, n, show_display=False, multisig=None):
    return client.call(proto.EthereumGetAddress(address_n=n, show_display=show_display))


@expect(proto.EthereumPublicKey)
def get_public_node(client, n, show_display=False):
    return client.call(
        proto.EthereumGetPublicKey(address_n=n, show_display=show_display)
    )


@session
def sign_tx(
    client,
    n,
    nonce,
    gas_price,
    gas_limit,
    to,
    value,
    data=None,
    chain_id=None,
    tx_type=None,
):
    msg = proto.EthereumSignTx(
        address_n=n,
        nonce=int_to_big_endian(nonce),
        gas_price=int_to_big_endian(gas_price),
        gas_limit=int_to_big_endian(gas_limit),
        value=int_to_big_endian(value),
    )

    if to:
        msg.to = to

    if data:
        msg.data_length = len(data)
        data, chunk = data[1024:], data[:1024]
        msg.data_initial_chunk = chunk

    if chain_id:
        msg.chain_id = chain_id

    if tx_type is not None:
        msg.tx_type = tx_type

    response = client.call(msg)

    while response.data_length is not None:
        data_length = response.data_length
        data, chunk = data[data_length:], data[:data_length]
        response = client.call(proto.EthereumTxAck(data_chunk=chunk))

    # https://github.com/trezor/trezor-core/pull/311
    # only signature bit returned. recalculate signature_v
    if response.signature_v <= 1:
        response.signature_v += 2 * chain_id + 35

    return response.signature_v, response.signature_r, response.signature_s


@expect(proto.EthereumMessageSignature)
def sign_message(client, n, message):
    message = normalize_nfc(message)
    return client.call(proto.EthereumSignMessage(address_n=n, message=message))


@expect(proto.EthereumTypedDataRequest)
def sign_typed_data(client, n, data_string):
    data = json.loads(data_string)
    response = client.call(proto.EthereumSignTypedData(address_n=n, num_members=2))

    while len(response.member_path) > 0:
        root_index = response.member_path[0]
        if root_index == 0:
            member_type = 'EIP712Domain'
            member_data = data['domain']
        elif root_index == 1:
            member_type = data['primaryType']
            member_data = data['message']
        else: 
            raise ValueError("Unknown root") # TODO do we need to signal the device?
        member_name = None
        for index in response.member_path[1:]:
            member_def = data['types'][member_type][index]
            member_name = member_def['name']
            member_type = member_def['type']
            member_data = member_data[member_def['name']]

        is_struct = member_type in data['types']
        response = client.call(proto.EthereumTypedDataAck(
            member_name=member_name,
            member_type=member_type,
            member_value=None if (is_struct) else str(member_data),
            num_members=None if (not is_struct) else len(data['types'][member_type])
        ))
    return response


def verify_message(client, address, signature, message):
    message = normalize_nfc(message)
    try:
        resp = client.call(
            proto.EthereumVerifyMessage(
                address=address, signature=signature, message=message
            )
        )
    except CallException as e:
        resp = e
    if isinstance(resp, proto.Success):
        return True
    return False
