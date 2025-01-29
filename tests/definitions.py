from __future__ import annotations

import io
import typing as t
from hashlib import sha256

from trezorlib import cosi, definitions, messages, protobuf

from .common import PRIVATE_KEYS_DEV


def make_eth_network(
    chain_id: int = 0,
    slip44: int = 0,
    symbol: str = "FAKE",
    name: str = "Fake network",
) -> messages.EthereumNetworkInfo:
    return messages.EthereumNetworkInfo(
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
) -> messages.EthereumTokenInfo:
    return messages.EthereumTokenInfo(
        symbol=symbol,
        decimals=decimals,
        address=address,
        chain_id=chain_id,
        name=name,
    )


def make_payload(
    data_type: messages.DefinitionType = messages.DefinitionType.ETHEREUM_NETWORK,
    timestamp: int = 0xFFFF_FFFF,
    message: (
        messages.EthereumNetworkInfo
        | messages.EthereumTokenInfo
        | messages.SolanaTokenInfo
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
    network: messages.EthereumNetworkInfo | None = None,
    chain_id: int = 0,
    slip44: int = 0,
    symbol: str = "FAKE",
    name: str = "Fake network",
) -> bytes:
    if network is None:
        network = make_eth_network(chain_id, slip44, symbol, name)
    payload = make_payload(
        data_type=messages.DefinitionType.ETHEREUM_NETWORK, message=network
    )
    proof, signature = sign_payload(payload, [])
    return payload + proof + signature


def encode_eth_token(
    token: messages.EthereumTokenInfo | None = None,
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
        data_type=messages.DefinitionType.ETHEREUM_TOKEN, message=token
    )
    proof, signature = sign_payload(payload, [])
    return payload + proof + signature


def make_eth_defs(
    network: bytes | None, token: bytes | None
) -> messages.EthereumDefinitions:
    return messages.EthereumDefinitions(
        encoded_network=network,
        encoded_token=token,
    )


def make_solana_token(
    symbol: str = "FakeTok",
    mint: bytes = b"\x00" * 32,
    name: str = "Fake token",
) -> messages.SolanaTokenInfo:
    return messages.SolanaTokenInfo(
        symbol=symbol,
        mint=mint,
        name=name,
    )


def encode_solana_token(
    token: messages.SolanaTokenInfo | None = None,
    symbol: str = "FakeTok",
    mint: bytes = b"\x00" * 32,
    name: str = "Fake token",
) -> bytes:
    if token is None:
        token = make_solana_token(symbol, mint, name)
    payload = make_payload(
        data_type=messages.DefinitionType.SOLANA_TOKEN, message=token
    )
    proof, signature = sign_payload(payload, [])
    return payload + proof + signature
