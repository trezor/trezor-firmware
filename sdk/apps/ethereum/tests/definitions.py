from __future__ import annotations

import io
import typing as t
from hashlib import sha256

from trezorlib import cosi, definitions, protobuf
from trezorlib.testing.common import PRIVATE_KEYS_DEV

from .generated import messages as ethereum_messages


def make_eth_network(
    chain_id: int = 0,
    slip44: int = 0,
    symbol: str = "FAKE",
    name: str = "Fake network",
) -> ethereum_messages.NetworkInfo:
    return ethereum_messages.NetworkInfo(
        chain_id=chain_id,
        slip44=slip44,
        symbol=symbol,
        name=name,
    )


def make_eth_token(
    symbol: str = "FAKE",
    decimals: int = 18,
    address: bytes = b"",
    chain_id: int = 0,
    name: str = "Fake token",
) -> ethereum_messages.TokenInfo:
    return ethereum_messages.TokenInfo(
        symbol=symbol,
        decimals=decimals,
        address=address,
        chain_id=chain_id,
        name=name,
    )


def make_payload(
    data_type: ethereum_messages.DefinitionType = ethereum_messages.DefinitionType.NETWORK,
    timestamp: int = 0xFFFF_FFFF,
    message: (
        ethereum_messages.NetworkInfo
        | ethereum_messages.TokenInfo
        | ethereum_messages.DisplayFormatInfo
        | bytes
    ) = make_eth_network(),
) -> bytes:
    if isinstance(message, bytes):
        message_bytes = message
    else:
        writer = io.BytesIO()
        protobuf.dump_message(writer, message)
        message_bytes = writer.getvalue()

    payload = definitions.DefinitionPayload(
        magic=b"trzd1",
        data_type=data_type,
        timestamp=timestamp,
        data=message_bytes,
    )
    return payload.build()


def sign_payload(
    payload: bytes,
    merkle_neighbors: list[bytes],
    threshold: int = 3,
) -> tuple[bytes, bytes]:
    digest = sha256(b"\x00" + payload).digest()
    merkle_proof = []
    for item in merkle_neighbors:
        left, right = min(digest, item), max(digest, item)
        digest = sha256(b"\x01" + left + right).digest()
        merkle_proof.append(digest)

    merkle_proof = len(merkle_proof).to_bytes(1, "little") + b"".join(merkle_proof)
    signature = cosi.sign_with_privkeys(digest, PRIVATE_KEYS_DEV[:threshold])
    sigmask = 0
    for i in range(threshold):
        sigmask |= 1 << i
    sigmask_byte = sigmask.to_bytes(1, "little")
    return merkle_proof, sigmask_byte + signature


def encode_eth_network(
    network: ethereum_messages.NetworkInfo | None = None,
    chain_id: int = 0,
    slip44: int = 0,
    symbol: str = "FAKE",
    name: str = "Fake network",
) -> bytes:
    if network is None:
        network = make_eth_network(chain_id, slip44, symbol, name)
    payload = make_payload(
        data_type=ethereum_messages.DefinitionType.NETWORK, message=network
    )
    proof, signature = sign_payload(payload, [])
    return payload + proof + signature


def encode_eth_token(
    token: ethereum_messages.TokenInfo | None = None,
    symbol: str = "FakeTok",
    decimals: int = 18,
    address: t.AnyStr = b"",
    chain_id: int = 0,
    name: str = "Fake token",
) -> bytes:
    if token is None:
        if isinstance(address, str):
            if address.startswith("0x"):
                address = address[2:]
            address = bytes.fromhex(address)  # type: ignore (typechecker is lying)
        token = make_eth_token(symbol, decimals, address, chain_id, name)  # type: ignore (typechecker is lying)
    payload = make_payload(
        data_type=ethereum_messages.DefinitionType.TOKEN, message=token
    )
    proof, signature = sign_payload(payload, [])
    return payload + proof + signature


def make_eth_defs(
    network: bytes | None, token: bytes | None
) -> ethereum_messages.EthereumDefinitions:
    return ethereum_messages.Definitions(
        encoded_network=network,
        encoded_token=token,
    )


def make_eth_display_format(
    chain_id: int = 0,
    address: t.AnyStr = b"",
    func_sig: bytes = b"",
    intent: str = "Fake intent",
    parameter_definitions: list[ethereum_messages.ABIValueInfo] | None = None,
    field_definitions: list[ethereum_messages.ERC7730FieldInfo] | None = None,
) -> ethereum_messages.DisplayFormatInfo:
    if isinstance(address, str):
        if address.startswith("0x"):
            address = address[2:]
        address_bytes = bytes.fromhex(address)
    else:
        address_bytes = address
    return ethereum_messages.DisplayFormatInfo(
        chain_id=chain_id,
        address=address_bytes,
        func_sig=func_sig,
        intent=intent,
        parameter_definitions=parameter_definitions or [],
        field_definitions=field_definitions or [],
    )


def encode_eth_display_format(
    display_format: ethereum_messages.DisplayFormatInfo,
) -> bytes:
    payload = make_payload(
        data_type=ethereum_messages.DefinitionType.DISPLAY_FORMAT,
        message=display_format,
    )
    proof, signature = sign_payload(payload, [])
    return payload + proof + signature
