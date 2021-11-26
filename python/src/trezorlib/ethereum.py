# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
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

import re
from typing import TYPE_CHECKING, Any, AnyStr, Dict, List, Optional, Tuple

from . import exceptions, messages
from .tools import expect, normalize_nfc, session

if TYPE_CHECKING:
    from .client import TrezorClient
    from .tools import Address
    from .protobuf import MessageType


def int_to_big_endian(value: int) -> bytes:
    return value.to_bytes((value.bit_length() + 7) // 8, "big")


def decode_hex(value: str) -> bytes:
    if value.startswith(("0x", "0X")):
        return bytes.fromhex(value[2:])
    else:
        return bytes.fromhex(value)


def sanitize_typed_data(data: dict) -> dict:
    """Remove properties from a message object that are not defined per EIP-712."""
    REQUIRED_KEYS = ("types", "primaryType", "domain", "message")
    sanitized_data = {key: data[key] for key in REQUIRED_KEYS}
    sanitized_data["types"].setdefault("EIP712Domain", [])
    return sanitized_data


def is_array(type_name: str) -> bool:
    return type_name[-1] == "]"


def typeof_array(type_name: str) -> str:
    return type_name[: type_name.rindex("[")]


def parse_type_n(type_name: str) -> int:
    """Parse N from type<N>. Example: "uint256" -> 256."""
    match = re.search(r"\d+$", type_name)
    if match:
        return int(match.group(0))
    else:
        raise ValueError(f"Could not parse type<N> from {type_name}.")


def parse_array_n(type_name: str) -> Optional[int]:
    """Parse N in type[<N>] where "type" can itself be an array type."""
    # sign that it is a dynamic array - we do not know <N>
    if type_name.endswith("[]"):
        return None

    start_idx = type_name.rindex("[") + 1
    return int(type_name[start_idx:-1])


def get_byte_size_for_int_type(int_type: str) -> int:
    return parse_type_n(int_type) // 8


def get_field_type(type_name: str, types: dict) -> messages.EthereumFieldType:
    data_type = None
    size = None
    entry_type = None
    struct_name = None

    if is_array(type_name):
        data_type = messages.EthereumDataType.ARRAY
        size = parse_array_n(type_name)
        member_typename = typeof_array(type_name)
        entry_type = get_field_type(member_typename, types)
        # Not supporting nested arrays currently
        if entry_type.data_type == messages.EthereumDataType.ARRAY:
            raise NotImplementedError("Nested arrays are not supported")
    elif type_name.startswith("uint"):
        data_type = messages.EthereumDataType.UINT
        size = get_byte_size_for_int_type(type_name)
    elif type_name.startswith("int"):
        data_type = messages.EthereumDataType.INT
        size = get_byte_size_for_int_type(type_name)
    elif type_name.startswith("bytes"):
        data_type = messages.EthereumDataType.BYTES
        size = None if type_name == "bytes" else parse_type_n(type_name)
    elif type_name == "string":
        data_type = messages.EthereumDataType.STRING
    elif type_name == "bool":
        data_type = messages.EthereumDataType.BOOL
    elif type_name == "address":
        data_type = messages.EthereumDataType.ADDRESS
    elif type_name in types:
        data_type = messages.EthereumDataType.STRUCT
        size = len(types[type_name])
        struct_name = type_name
    else:
        raise ValueError(f"Unsupported type name: {type_name}")

    return messages.EthereumFieldType(
        data_type=data_type,
        size=size,
        entry_type=entry_type,
        struct_name=struct_name,
    )


def encode_data(value: Any, type_name: str) -> bytes:
    if type_name.startswith("bytes"):
        return decode_hex(value)
    elif type_name == "string":
        return value.encode()
    elif type_name.startswith(("int", "uint")):
        byte_length = get_byte_size_for_int_type(type_name)
        return int(value).to_bytes(
            byte_length, "big", signed=type_name.startswith("int")
        )
    elif type_name == "bool":
        if not isinstance(value, bool):
            raise ValueError(f"Invalid bool value - {value}")
        return int(value).to_bytes(1, "big")
    elif type_name == "address":
        return decode_hex(value)

    # We should be receiving only atomic, non-array types
    raise ValueError(f"Unsupported data type for direct field encoding: {type_name}")


# ====== Client functions ====== #


@expect(messages.EthereumAddress, field="address", ret_type=str)
def get_address(
    client: "TrezorClient", n: "Address", show_display: bool = False
) -> "MessageType":
    return client.call(
        messages.EthereumGetAddress(address_n=n, show_display=show_display)
    )


@expect(messages.EthereumPublicKey)
def get_public_node(
    client: "TrezorClient", n: "Address", show_display: bool = False
) -> "MessageType":
    return client.call(
        messages.EthereumGetPublicKey(address_n=n, show_display=show_display)
    )


@session
def sign_tx(
    client: "TrezorClient",
    n: "Address",
    nonce: int,
    gas_price: int,
    gas_limit: int,
    to: str,
    value: int,
    data: Optional[bytes] = None,
    chain_id: Optional[int] = None,
    tx_type: Optional[int] = None,
) -> Tuple[int, bytes, bytes]:
    if chain_id is None:
        raise exceptions.TrezorException("Chain ID cannot be undefined")

    msg = messages.EthereumSignTx(
        address_n=n,
        nonce=int_to_big_endian(nonce),
        gas_price=int_to_big_endian(gas_price),
        gas_limit=int_to_big_endian(gas_limit),
        value=int_to_big_endian(value),
        to=to,
        chain_id=chain_id,
        tx_type=tx_type,
    )

    if data is None:
        data = b""

    msg.data_length = len(data)
    data, chunk = data[1024:], data[:1024]
    msg.data_initial_chunk = chunk

    response = client.call(msg)
    assert isinstance(response, messages.EthereumTxRequest)

    while response.data_length is not None:
        data_length = response.data_length
        data, chunk = data[data_length:], data[:data_length]
        response = client.call(messages.EthereumTxAck(data_chunk=chunk))
        assert isinstance(response, messages.EthereumTxRequest)

    assert response.signature_v is not None
    assert response.signature_r is not None
    assert response.signature_s is not None

    # https://github.com/trezor/trezor-core/pull/311
    # only signature bit returned. recalculate signature_v
    if response.signature_v <= 1:
        response.signature_v += 2 * chain_id + 35

    return response.signature_v, response.signature_r, response.signature_s


@session
def sign_tx_eip1559(
    client: "TrezorClient",
    n: "Address",
    *,
    nonce: int,
    gas_limit: int,
    to: str,
    value: int,
    data: bytes = b"",
    chain_id: int,
    max_gas_fee: int,
    max_priority_fee: int,
    access_list: Optional[List[messages.EthereumAccessList]] = None,
) -> Tuple[int, bytes, bytes]:
    length = len(data)
    data, chunk = data[1024:], data[:1024]
    msg = messages.EthereumSignTxEIP1559(
        address_n=n,
        nonce=int_to_big_endian(nonce),
        gas_limit=int_to_big_endian(gas_limit),
        value=int_to_big_endian(value),
        to=to,
        chain_id=chain_id,
        max_gas_fee=int_to_big_endian(max_gas_fee),
        max_priority_fee=int_to_big_endian(max_priority_fee),
        access_list=access_list,
        data_length=length,
        data_initial_chunk=chunk,
    )

    response = client.call(msg)
    assert isinstance(response, messages.EthereumTxRequest)

    while response.data_length is not None:
        data_length = response.data_length
        data, chunk = data[data_length:], data[:data_length]
        response = client.call(messages.EthereumTxAck(data_chunk=chunk))
        assert isinstance(response, messages.EthereumTxRequest)

    assert response.signature_v is not None
    assert response.signature_r is not None
    assert response.signature_s is not None
    return response.signature_v, response.signature_r, response.signature_s


@expect(messages.EthereumMessageSignature)
def sign_message(
    client: "TrezorClient", n: "Address", message: AnyStr
) -> "MessageType":
    return client.call(
        messages.EthereumSignMessage(address_n=n, message=normalize_nfc(message))
    )


@expect(messages.EthereumTypedDataSignature)
def sign_typed_data(
    client: "TrezorClient",
    n: "Address",
    data: Dict[str, Any],
    *,
    metamask_v4_compat: bool = True,
) -> "MessageType":
    data = sanitize_typed_data(data)
    types = data["types"]

    request = messages.EthereumSignTypedData(
        address_n=n,
        primary_type=data["primaryType"],
        metamask_v4_compat=metamask_v4_compat,
    )
    response = client.call(request)

    # Sending all the types
    while isinstance(response, messages.EthereumTypedDataStructRequest):
        struct_name = response.name

        members: List["messages.EthereumStructMember"] = []
        for field in types[struct_name]:
            field_type = get_field_type(field["type"], types)
            struct_member = messages.EthereumStructMember(
                type=field_type,
                name=field["name"],
            )
            members.append(struct_member)

        request = messages.EthereumTypedDataStructAck(members=members)
        response = client.call(request)

    # Sending the whole message that should be signed
    while isinstance(response, messages.EthereumTypedDataValueRequest):
        root_index = response.member_path[0]
        # Index 0 is for the domain data, 1 is for the actual message
        if root_index == 0:
            member_typename = "EIP712Domain"
            member_data = data["domain"]
        elif root_index == 1:
            member_typename = data["primaryType"]
            member_data = data["message"]
        else:
            client.cancel()
            raise exceptions.TrezorException("Root index can only be 0 or 1")

        # It can be asking for a nested structure (the member path being [X, Y, Z, ...])
        # TODO: what to do when the value is missing (for example in recursive types)?
        for index in response.member_path[1:]:
            if isinstance(member_data, dict):
                member_def = types[member_typename][index]
                member_typename = member_def["type"]
                member_data = member_data[member_def["name"]]
            elif isinstance(member_data, list):
                member_typename = typeof_array(member_typename)
                member_data = member_data[index]

        # If we were asked for a list, first sending its length and we will be receiving
        # requests for individual elements later
        if isinstance(member_data, list):
            # Sending the length as uint16
            encoded_data = len(member_data).to_bytes(2, "big")
        else:
            encoded_data = encode_data(member_data, member_typename)

        request = messages.EthereumTypedDataValueAck(value=encoded_data)
        response = client.call(request)

    return response


def verify_message(
    client: "TrezorClient", address: str, signature: bytes, message: AnyStr
) -> bool:
    try:
        resp = client.call(
            messages.EthereumVerifyMessage(
                address=address, signature=signature, message=normalize_nfc(message)
            )
        )
    except exceptions.TrezorFailure:
        return False
    return isinstance(resp, messages.Success)
