import io  # noqa: F401
from binascii import unhexlify
from hashlib import sha256
from typing import Optional, Union

import ed25519

from trezorlib import messages, protobuf

DEFINITIONS_DEV_PRIVATE_KEY = unhexlify(
    "4141414141414141414141414141414141414141414141414141414141414141"
)


NETWORKS = {
    # chain_id: network info
    1: messages.EthereumNetworkInfo(
        chain_id=1,
        slip44=60,
        shortcut="ETH",
        name="Ethereum",
    ),
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
    60: messages.EthereumNetworkInfo(
        chain_id=60,
        slip44=6060,
        shortcut="GO",
        name="GoChain",
    ),
    61: messages.EthereumNetworkInfo(
        chain_id=61,
        slip44=61,
        shortcut="ETC",
        name="Ethereum Classic",
    ),
    888: messages.EthereumNetworkInfo(
        chain_id=888,
        slip44=5718350,
        shortcut="WAN",
        name="Wanchain",
    ),
    28945486: messages.EthereumNetworkInfo(
        chain_id=28945486,
        slip44=344,
        shortcut="AUX",
        name="Auxilium Network",
    ),
    3125659152: messages.EthereumNetworkInfo(
        chain_id=3125659152,
        slip44=164,
        shortcut="PIRL",
        name="Pirl",
    ),
    11297108109: messages.EthereumNetworkInfo(
        chain_id=11297108109,
        slip44=60,
        shortcut="PALM",
        name="Palm",
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
        "dac17f958d2ee523a2206206994597c13d831ec7": messages.EthereumTokenInfo(
            symbol="USDT",
            decimals=6,
            address=unhexlify("dac17f958d2ee523a2206206994597c13d831ec7"),
            chain_id=1,
            name="Tether",
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


def get_reference_ethereum_network_info(
    chain_id: Optional[int] = None, slip44: Optional[int] = None
) -> Optional[messages.EthereumNetworkInfo]:
    if not (chain_id is None) != (slip44 is None):  # not XOR
        raise ValueError("chain_id and slip44 arguments are exclusive")

    # resolve network
    if chain_id is not None:
        return NETWORKS.get(chain_id)
    else:  # slip44 is not None
        for _, network in NETWORKS.items():
            if network.slip44 == slip44:
                return network

    return None


def get_reference_ethereum_token_info(
    chain_id: int, token_address: str
) -> Optional[messages.EthereumTokenInfo]:
    if token_address.startswith("0x"):
        token_address = token_address[2:]
    return TOKENS.get(chain_id, {}).get(token_address)


def _serialize_eth_info(
    info: Union[messages.EthereumNetworkInfo, messages.EthereumTokenInfo],
    data_type_num: messages.EthereumDefinitionType,
    timestamp: Optional[int] = None,
) -> bytes:
    ser = b"trzd1"
    ser += data_type_num.to_bytes(1, "big")
    if timestamp is not None:
        ser += timestamp.to_bytes(4, "big")
    else:
        # set data version to max to avoid "outdated" definition errors
        ser += b"\xff" * 4

    # serialize message
    buf = io.BytesIO()
    protobuf.dump_message(buf, info)
    msg = buf.getvalue()
    # write the length of encoded protobuf message
    ser += len(msg).to_bytes(2, "big")
    ser += msg

    # add Merkle tree proof length and signature
    hash = sha256(b"\x00" + ser).digest()
    ser += b"\x00"
    ser += ed25519.SigningKey(DEFINITIONS_DEV_PRIVATE_KEY).sign(hash)

    return ser


def get_encoded_network_definition(
    chain_id: Optional[int] = None,
    slip44: Optional[int] = None,
    timestamp: Optional[int] = None,
) -> Optional[bytes]:
    info = get_reference_ethereum_network_info(chain_id, slip44)

    if info is None:
        return None

    return _serialize_eth_info(info, messages.EthereumDefinitionType.NETWORK, timestamp)


def get_encoded_token_definition(
    chain_id: int,
    token_address: str,
    timestamp: Optional[int] = None,
) -> Optional[bytes]:
    info = get_reference_ethereum_token_info(chain_id, token_address)

    if info is None:
        return None

    return _serialize_eth_info(info, messages.EthereumDefinitionType.TOKEN, timestamp)
