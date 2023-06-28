from ubinascii import unhexlify  # noqa: F401

from trezor import messages, protobuf
from trezor.crypto import cosi
from trezor.crypto.curve import ed25519
from trezor.crypto.hashlib import sha256
from trezor.enums import EthereumDefinitionType

PRIVATE_KEYS_DEV = [byte * 32 for byte in (b"\xdd", b"\xde", b"\xdf")]


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
    prefix: bytes = b"trzd1",
    data_type: EthereumDefinitionType = EthereumDefinitionType.NETWORK,
    timestamp: int = 0xFFFF_FFFF,
    message: messages.EthereumNetworkInfo
    | messages.EthereumTokenInfo
    | bytes = make_network(),
) -> bytes:
    payload = prefix
    payload += data_type.to_bytes(1, "little")
    payload += timestamp.to_bytes(4, "little")
    if isinstance(message, bytes):
        message_bytes = message
    else:
        message_bytes = protobuf.dump_message_buffer(message)
    payload += len(message_bytes).to_bytes(2, "little")
    payload += message_bytes
    return payload


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

    nonces, commits, pubkeys = [], [], []
    for i, private_key in enumerate(PRIVATE_KEYS_DEV[:threshold]):
        nonce, commit = cosi.commit()
        pubkey = ed25519.publickey(private_key)
        nonces.append(nonce)
        commits.append(commit)
        pubkeys.append(pubkey)

    global_commit = cosi.combine_publickeys(commits)
    global_pubkey = cosi.combine_publickeys(pubkeys)
    sigmask = 0
    signatures = []
    for i, nonce in enumerate(nonces):
        sigmask |= 1 << i
        sig = cosi.sign(
            PRIVATE_KEYS_DEV[i], digest, nonce, global_commit, global_pubkey
        )
        signatures.append(sig)

    signature = cosi.combine_signatures(global_commit, signatures)
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
    payload = make_payload(data_type=EthereumDefinitionType.NETWORK, message=network)
    proof, signature = sign_payload(payload, [])
    return payload + proof + signature


def encode_token(
    token: messages.EthereumTokenInfo | None = None,
    symbol: str = "FAKE",
    decimals: int = 18,
    address: bytes = b"",
    chain_id: int = 0,
    name: str = "Fake token",
) -> bytes:
    if token is None:
        token = make_token(symbol, decimals, address, chain_id, name)
    payload = make_payload(data_type=EthereumDefinitionType.TOKEN, message=token)
    proof, signature = sign_payload(payload, [])
    return payload + proof + signature
