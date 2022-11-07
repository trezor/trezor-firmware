from ubinascii import unhexlify  # noqa: F401

from apps.ethereum import networks, tokens
from trezor import messages, protobuf
from trezor.enums import EthereumDefinitionType
from trezor.crypto.curve import ed25519
from trezor.crypto.hashlib import sha256

DEFINITIONS_DEV_PRIVATE_KEY = unhexlify(
    "4141414141414141414141414141414141414141414141414141414141414141"
)


NETWORKS = {
    # chain_id: network info
    8: messages.EthereumNetworkInfo(
        chain_id=8,
        slip44=108,
        shortcut="UBQ",
        name="Ubiq",
    ),
    31: messages.EthereumNetworkInfo(
        chain_id=31,
        slip44=1,
        shortcut="tRBTC",
        name="RSK Testnet",
    ),
}


TOKENS = {
    # chain_id: { address: token info, address: token info,... }
    1: {
        "d0d6d6c5fe4a677d343cc433536bb717bae167dd": messages.EthereumTokenInfo(
            symbol="ADT",
            decimals=9,
            address=unhexlify("d0d6d6c5fe4a677d343cc433536bb717bae167dd"),
            chain_id=1,
            name="adChain",
        ),
        "a33e729bf4fdeb868b534e1f20523463d9c46bee": messages.EthereumTokenInfo(
            symbol="ICO",
            decimals=10,
            address=unhexlify("a33e729bf4fdeb868b534e1f20523463d9c46bee"),
            chain_id=1,
            name="ICO",
        ),
    },
    8: {
        "20e3dd746ddf519b23ffbbb6da7a5d33ea6349d6": messages.EthereumTokenInfo(
            symbol="SPHR",
            decimals=8,
            address=unhexlify("20e3dd746ddf519b23ffbbb6da7a5d33ea6349d6"),
            chain_id=8,
            name="Sphere",
        ),
    },
}


def construct_network_info(chain_id: int = 0, slip44: int = 0, shortcut: str = "", name: str = "") -> messages.EthereumNetworkInfo:
    return messages.EthereumNetworkInfo(
        chain_id=chain_id,
        slip44=slip44,
        shortcut=shortcut,
        name=name,
    )


def get_reference_ethereum_network_info(chain_id: int | None = None, slip44: int | None = None) -> messages.EthereumNetworkInfo:
    if not ((chain_id is None) != (slip44 is None)):  # not XOR
        raise ValueError("chain_id and slip44 arguments are exclusive")

    network = None

    # resolve network
    if chain_id is not None:
        network = networks.by_chain_id(chain_id)

        if network is None:
            network = NETWORKS.get(chain_id)
    else: # slip44 is not None
        network = networks.by_slip44(slip44)

        if network is None:
            for _, network in NETWORKS.items():
                if network.slip44 == slip44:
                    return network

    return network if network else networks.UNKNOWN_NETWORK


def get_reference_ethereum_token_info(chain_id: int, token_address: str) -> messages.EthereumTokenInfo:
    token = tokens.token_by_chain_address(chain_id, unhexlify(token_address))

    if token is None:
        token = TOKENS.get(chain_id, {}).get(token_address)

    return token if token else tokens.UNKNOWN_TOKEN


def _serialize_eth_info(
    info: messages.EthereumNetworkInfo | messages.EthereumTokenInfo,
    data_type_num: messages.EthereumDefinitionType,
    timestamp: int | None = None,
) -> bytes:
    ser = b"trzd1"
    ser += data_type_num.to_bytes(1, "big")
    if timestamp is not None:
        ser += timestamp.to_bytes(4, "big")
    else:
        # set data version to max to avoid "outdated" definition errors
        ser += b'\xff' * 4

    # serialize message
    length = protobuf.encoded_length(info)
    buffer = bytearray(length)
    protobuf.encode(buffer, info)
    # write the length of encoded protobuf message
    ser += length.to_bytes(2, "big")
    ser += buffer

    # add Merkle tree proof length and signature
    hash = sha256(b"\x00" + ser).digest()
    ser += b'\x00'
    ser += ed25519.sign(DEFINITIONS_DEV_PRIVATE_KEY, hash)

    return ser


def get_encoded_network_definition(
    network_info: messages.EthereumNetworkInfo,
    timestamp: int | None = None,
) -> bytes:
    return _serialize_eth_info(network_info, EthereumDefinitionType.NETWORK, timestamp)


def get_encoded_token_definition(
    token_info: messages.EthereumTokenInfo,
    timestamp: int | None = None,
) -> bytes:
    return _serialize_eth_info(token_info, EthereumDefinitionType.TOKEN, timestamp)
