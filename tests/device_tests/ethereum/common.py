from __future__ import annotations

import io
import typing as t
from hashlib import sha256

from trezorlib import cosi, definitions, messages, protobuf

PRIVATE_KEYS_DEV = [byte * 32 for byte in (b"\xdd", b"\xde", b"\xdf")]


def sign_with_privkeys(digest: bytes, privkeys: t.Sequence[bytes]) -> bytes:
    """Locally produce a CoSi signature."""
    pubkeys = [cosi.pubkey_from_privkey(sk) for sk in privkeys]
    nonces = [cosi.get_nonce(sk, digest, i) for i, sk in enumerate(privkeys)]

    global_pk = cosi.combine_keys(pubkeys)
    global_R = cosi.combine_keys(R for _, R in nonces)

    sigs = [
        cosi.sign_with_privkey(digest, sk, global_pk, r, global_R)
        for sk, (r, _) in zip(privkeys, nonces)
    ]

    return cosi.combine_sig(global_R, sigs)


def make_network(
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


def make_token(
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
    data_type: messages.EthereumDefinitionType = messages.EthereumDefinitionType.NETWORK,
    timestamp: int = 0xFFFF_FFFF,
    message: messages.EthereumNetworkInfo
    | messages.EthereumTokenInfo
    | bytes = make_network(),
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
    signature = sign_with_privkeys(digest, PRIVATE_KEYS_DEV[:threshold])
    sigmask = 0
    for i in range(threshold):
        sigmask |= 1 << i
    sigmask_byte = sigmask.to_bytes(1, "little")
    return merkle_proof, sigmask_byte + signature


def encode_network(
    network: messages.EthereumNetworkInfo | None = None,
    chain_id: int = 0,
    slip44: int = 0,
    symbol: str = "FAKE",
    name: str = "Fake network",
) -> bytes:
    if network is None:
        network = make_network(chain_id, slip44, symbol, name)
    payload = make_payload(
        data_type=messages.EthereumDefinitionType.NETWORK, message=network
    )
    proof, signature = sign_payload(payload, [])
    return payload + proof + signature


def encode_token(
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
        token = make_token(symbol, decimals, address, chain_id, name)  # type: ignore (typechecker is lying)
    payload = make_payload(
        data_type=messages.EthereumDefinitionType.TOKEN, message=token
    )
    proof, signature = sign_payload(payload, [])
    return payload + proof + signature


def make_defs(
    network: bytes | None, token: bytes | None
) -> messages.EthereumDefinitions:
    return messages.EthereumDefinitions(
        encoded_network=network,
        encoded_token=token,
    )
