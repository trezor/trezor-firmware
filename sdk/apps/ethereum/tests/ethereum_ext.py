# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
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

import io
import re
from typing import TYPE_CHECKING, Any, AnyStr, Dict, List, Optional, Tuple

from trezorlib.messages import ExtAppMessage, ExtAppResponse, Failure
from trezorlib import exceptions, protobuf
from trezorlib.tools import prepare_message_bytes


from .generated import messages as ethereum_messages


if TYPE_CHECKING:
    from trezorlib.client import Session
    from trezorlib.tools import Address


def message_id(msg: type[protobuf.MessageType] | ethereum_messages.MessageType) -> int:
    """Return app-specific numeric message ID for a message class or instance."""
    if isinstance(msg, type):
        name = msg.__name__
    else:
        name = msg.__class__.__name__

    try:
        return int(ethereum_messages.MessageType[name])
    except KeyError as e:
        raise ValueError(f"Unknown message type: {name}") from e


def message_type(msg_id: int) -> type[protobuf.MessageType]:
    """Convert message ID (int) to message class type."""
    try:
        enum_name = ethereum_messages.MessageType(msg_id).name
        return getattr(ethereum_messages, enum_name)
    except ValueError as e:
        raise ValueError(f"Unknown message ID: {msg_id}") from e


def call_ext(
    session: "Session",
    instance_id: int,
    *,
    msg_data: ethereum_messages.MessageType,
    expect: list[type[ethereum_messages.MessageType]],
    timeout: float | None = None,
) -> Any:
    """Call a method on this session, process and return the response."""

    # Serialize to bytes
    buf = io.BytesIO()
    protobuf.dump_message(buf, msg_data)

    msg = ExtAppMessage(
        instance_id=instance_id,
        message_id=message_id(msg_data),
        data=buf.getvalue(),
    )
    if session.is_invalid:
        raise exceptions.InvalidSessionError(session.id)
    with session:
        resp = session.client._call(
            session, msg, expect=ExtAppResponse, timeout=timeout
        )
        buf = io.BytesIO(resp.data)

        assert isinstance(expect, list)
        assert len(expect) > 0

        expect_ids = [message_id(cls) for cls in expect]
        try:
            # Find the index of the matching message ID
            idx = expect_ids.index(resp.message_id)

            return protobuf.load_message(buf, expect[idx])
        except Exception as _e:
            raise exceptions.TrezorFailure(
                failure=Failure(message="Unexpected response type")
            )


def int_to_big_endian(value: int) -> bytes:
    """Encode integer into minimal-length big-endian bytes."""
    return value.to_bytes((value.bit_length() + 7) // 8, "big")


def decode_hex(value: str) -> bytes:
    """Decode hex string into bytes, accepting optional 0x/0X prefix."""
    if value.startswith(("0x", "0X")):
        return bytes.fromhex(value[2:])
    else:
        return bytes.fromhex(value)


def sanitize_typed_data(data: dict) -> dict:
    """Remove properties from a message object that are not defined per EIP-712."""
    required_keys = ("types", "primaryType", "domain", "message")
    sanitized_data = {key: data[key] for key in required_keys}
    sanitized_data["types"].setdefault("EIP712Domain", [])
    return sanitized_data


def is_array(type_name: str) -> bool:
    """Return True if Solidity/EIP-712 type denotes an array."""
    return type_name[-1] == "]"


def typeof_array(type_name: str) -> str:
    """Return element type for an array type, e.g. uint256[] -> uint256."""
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
    """Return byte size for int/uint type, e.g. uint256 -> 32."""
    return parse_type_n(int_type) // 8


def get_field_type(type_name: str, types: dict) -> ethereum_messages.FieldType:
    """Map EIP-712 type name to firmware FieldType descriptor."""
    data_type = None
    size = None
    entry_type = None
    struct_name = None

    if is_array(type_name):
        data_type = ethereum_messages.DataType.ARRAY
        size = parse_array_n(type_name)
        member_typename = typeof_array(type_name)
        entry_type = get_field_type(member_typename, types)
        # Not supporting nested arrays currently
        if entry_type.data_type == ethereum_messages.DataType.ARRAY:
            raise NotImplementedError("Nested arrays are not supported")
    elif type_name.startswith("uint"):
        data_type = ethereum_messages.DataType.UINT
        size = get_byte_size_for_int_type(type_name)
    elif type_name.startswith("int"):
        data_type = ethereum_messages.DataType.INT
        size = get_byte_size_for_int_type(type_name)
    elif type_name.startswith("bytes"):
        data_type = ethereum_messages.DataType.BYTES
        size = None if type_name == "bytes" else parse_type_n(type_name)
    elif type_name == "string":
        data_type = ethereum_messages.DataType.STRING
    elif type_name == "bool":
        data_type = ethereum_messages.DataType.BOOL
    elif type_name == "address":
        data_type = ethereum_messages.DataType.ADDRESS
    elif type_name in types:
        data_type = ethereum_messages.DataType.STRUCT
        size = len(types[type_name])
        struct_name = type_name
    else:
        raise ValueError(f"Unsupported type name: {type_name}")

    return ethereum_messages.FieldType(
        data_type=data_type,
        size=size,
        entry_type=entry_type,
        struct_name=struct_name,
    )


def encode_data(value: Any, type_name: str) -> bytes:
    """Encode atomic typed-data value to wire bytes for TypedDataValueAck."""
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


def get_address(*args: Any, **kwargs: Any) -> str:
    """Return Ethereum address string from GetAddress response."""
    resp = get_authenticated_address(*args, **kwargs)
    assert resp.address is not None
    return resp.address


def get_authenticated_address(
    session: "Session",
    instance_id: int,
    n: "Address",
    show_display: bool = False,
    encoded_network: Optional[bytes] = None,
    chunkify: bool = False,
) -> ethereum_messages.Address:
    """Request Ethereum address (optionally displayed) with full response payload."""
    return call_ext(
        session,
        instance_id,
        msg_data=ethereum_messages.GetAddress(
            address_n=n,
            show_display=show_display,
            encoded_network=encoded_network,
            chunkify=chunkify,
        ),
        expect=[ethereum_messages.Address],
    )


def get_public_node(
    session: "Session", instance_id: int, n: "Address", show_display: bool = False
) -> ethereum_messages.PublicKey:
    """Request Ethereum public node/public key for a derivation path."""
    return call_ext(
        session,
        instance_id,
        msg_data=ethereum_messages.GetPublicKey(address_n=n, show_display=show_display),
        expect=[ethereum_messages.PublicKey],
    )


def sign_tx(
    session: "Session",
    instance_id: int,
    n: "Address",
    nonce: int,
    gas_price: int,
    gas_limit: int,
    to: str,
    value: int,
    data: Optional[bytes] = None,
    chain_id: Optional[int] = None,
    tx_type: Optional[int] = None,
    definitions: Optional[ethereum_messages.Definitions] = None,
    chunkify: bool = False,
    payment_req: Optional[ethereum_messages.PaymentRequest] = None,
) -> Tuple[int, bytes, bytes]:
    """Sign legacy/EIP-2930 style transaction and return (v, r, s)."""
    if chain_id is None:
        raise exceptions.TrezorException("Chain ID cannot be undefined")

    msg = ethereum_messages.SignTx(
        address_n=n,
        nonce=int_to_big_endian(nonce),
        gas_price=int_to_big_endian(gas_price),
        gas_limit=int_to_big_endian(gas_limit),
        value=int_to_big_endian(value),
        to=to,
        chain_id=chain_id,
        tx_type=tx_type,
        definitions=definitions,
        chunkify=chunkify,
        payment_req=payment_req,
    )

    if data is None:
        data = b""

    msg.data_length = len(data)
    data, chunk = data[1024:], data[:1024]
    msg.data_initial_chunk = chunk

    response = call_ext(
        session,
        instance_id,
        msg_data=msg,
        expect=[ethereum_messages.TxRequest],
    )

    while response.data_length is not None:
        data_length = response.data_length
        data, chunk = data[data_length:], data[:data_length]
        response = call_ext(
            session,
            instance_id,
            msg_data=ethereum_messages.TxAck(data_chunk=chunk),
            expect=[ethereum_messages.TxRequest],
        )

    assert response.signature_v is not None
    assert response.signature_r is not None
    assert response.signature_s is not None

    # https://github.com/trezor/trezor-core/pull/311
    # only signature bit returned. recalculate signature_v
    if response.signature_v <= 1:
        response.signature_v += 2 * chain_id + 35

    return response.signature_v, response.signature_r, response.signature_s


def sign_tx_eip1559(
    session: "Session",
    instance_id: int,
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
    access_list: Optional[List[ethereum_messages.AccessList]] = None,
    definitions: Optional[ethereum_messages.Definitions] = None,
    chunkify: bool = False,
    payment_req: Optional[ethereum_messages.PaymentRequest] = None,
) -> Tuple[int, bytes, bytes]:
    """Sign EIP-1559 transaction and return (v, r, s)."""
    length = len(data)
    data, chunk = data[1024:], data[:1024]
    msg = ethereum_messages.SignTxEIP1559(
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
        definitions=definitions,
        chunkify=chunkify,
        payment_req=payment_req,
    )

    response = call_ext(
        session,
        instance_id,
        msg_data=msg,
        expect=[ethereum_messages.TxRequest],
    )

    while response.data_length is not None:
        data_length = response.data_length
        data, chunk = data[data_length:], data[:data_length]
        response = call_ext(
            session,
            instance_id,
            msg_data=ethereum_messages.TxAck(data_chunk=chunk),
            expect=[ethereum_messages.TxRequest],
        )

    assert response.signature_v is not None
    assert response.signature_r is not None
    assert response.signature_s is not None
    return response.signature_v, response.signature_r, response.signature_s


def sign_message(
    session: "Session",
    instance_id: int,
    n: "Address",
    message: AnyStr,
    encoded_network: Optional[bytes] = None,
    chunkify: bool = False,
) -> ethereum_messages.MessageSignature:
    """Sign an arbitrary message with Ethereum personal-sign semantics."""
    return call_ext(
        session,
        instance_id,
        msg_data=ethereum_messages.SignMessage(
            address_n=n,
            message=prepare_message_bytes(message),
            encoded_network=encoded_network,
            chunkify=chunkify,
        ),
        expect=[ethereum_messages.MessageSignature],
    )


def sign_typed_data(
    session: "Session",
    instance_id: int,
    n: "Address",
    data: Dict[str, Any],
    *,
    metamask_v4_compat: bool = True,
    definitions: Optional[ethereum_messages.Definitions] = None,
    show_message_hash: Optional[bytes] = None,
) -> ethereum_messages.TypedDataSignature:
    """Sign EIP-712 typed data via interactive struct/value request flow."""
    data = sanitize_typed_data(data)
    types = data["types"]

    request = ethereum_messages.SignTypedData(
        address_n=n,
        primary_type=data["primaryType"],
        metamask_v4_compat=metamask_v4_compat,
        definitions=definitions,
    )
    if show_message_hash is not None:
        request.show_message_hash = show_message_hash

    response = call_ext(
        session,
        instance_id,
        msg_data=request,
        expect=[
            ethereum_messages.TypedDataStructRequest,
            ethereum_messages.TypedDataValueRequest,
            ethereum_messages.TypedDataSignature,
        ],
    )

    # Sending all the types
    while isinstance(response, ethereum_messages.TypedDataStructRequest):
        struct_name = response.name

        members: List["ethereum_messages.StructMember"] = []
        for field in types[struct_name]:
            field_type = get_field_type(field["type"], types)
            struct_member = ethereum_messages.StructMember(
                type=field_type,
                name=field["name"],
            )
            members.append(struct_member)

        request = ethereum_messages.TypedDataStructAck(members=members)
        response = call_ext(
            session,
            instance_id,
            msg_data=request,
            expect=[
                ethereum_messages.TypedDataStructRequest,
                ethereum_messages.TypedDataValueRequest,
                ethereum_messages.TypedDataSignature,
            ],
        )

    # Sending the whole message that should be signed
    while isinstance(response, ethereum_messages.TypedDataValueRequest):
        root_index = response.member_path[0]
        # Index 0 is for the domain data, 1 is for the actual message
        if root_index == 0:
            member_typename = "EIP712Domain"
            member_data = data["domain"]
        elif root_index == 1:
            member_typename = data["primaryType"]
            member_data = data["message"]
        else:
            session.cancel()
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

        request = ethereum_messages.TypedDataValueAck(value=encoded_data)
        response = call_ext(
            session,
            instance_id,
            msg_data=request,
            expect=[
                ethereum_messages.TypedDataValueRequest,
                ethereum_messages.TypedDataSignature,
            ],
        )

    return ethereum_messages.TypedDataSignature.ensure_isinstance(response)


def verify_message(
    session: "Session",
    instance_id: int,
    address: str,
    signature: bytes,
    message: AnyStr,
    chunkify: bool = False,
) -> bool:
    """Verify Ethereum message signature; return False on firmware verification failure."""
    try:
        call_ext(
            session,
            instance_id,
            msg_data=ethereum_messages.VerifyMessage(
                address=address,
                signature=signature,
                message=prepare_message_bytes(message),
                chunkify=chunkify,
            ),
            expect=[ethereum_messages.Success],
        )
        return True
    except exceptions.TrezorFailure:
        return False


def sign_typed_data_hash(
    session: "Session",
    instance_id: int,
    n: "Address",
    domain_hash: bytes,
    message_hash: Optional[bytes],
    encoded_network: Optional[bytes] = None,
) -> ethereum_messages.TypedDataSignature:
    """Sign precomputed EIP-712 domain/message hashes."""
    return call_ext(
        session,
        instance_id,
        msg_data=ethereum_messages.SignTypedHash(
            address_n=n,
            domain_separator_hash=domain_hash,
            message_hash=message_hash,
            encoded_network=encoded_network,
        ),
        expect=[ethereum_messages.TypedDataSignature],
    )


def resp_filter(msg: protobuf.MessageType) -> protobuf.MessageType:
    """Decode ExtAppResponse payload into concrete generated message instance."""
    if isinstance(msg, ExtAppResponse):
        message_type_cls = message_type(msg.message_id)
        return protobuf.load_message(io.BytesIO(msg.data), message_type_cls)
    else:
        return msg
