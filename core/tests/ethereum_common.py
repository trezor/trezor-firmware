import uio
from ubinascii import unhexlify  # noqa: F401

from apps.ethereum import networks, tokens
from common import COMMON_FIXTURES_DIR
from trezor import messages


FIXTURES_DEFINITIONS_DIR=COMMON_FIXTURES_DIR + "/ethereum/definitions-latest"
# following constants for "DEFS" were copied from "../../python/src/trezorlib/ethereum.py"
DEFS_NETWORK_BY_CHAINID_LOOKUP_TYPE = "by_chain_id"
DEFS_NETWORK_BY_SLIP44_LOOKUP_TYPE = "by_slip44"
DEFS_NETWORK_URI_NAME = "network.dat"
DEFS_TOKEN_URI_NAME = "token_{hex_address}.dat"

EXPECTED_FORMAT_VERSION = 1
EXPECTED_DATA_VERSION = 1663054984 # unix epoch time


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


SLIP44_TO_CHAIN_ID_MAP = {
    1: 31,
    108: 8,
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
            cid = SLIP44_TO_CHAIN_ID_MAP.get(slip44)
            if cid is not None:
                return NETWORKS.get(cid[0])

    return network if network else etworks.UNKNOWN_NETWORK


def get_reference_ethereum_token_info(chain_id: int, token_address: str) -> messages.EthereumTokenInfo:
    token = tokens.token_by_chain_address(chain_id, unhexlify(token_address))

    if token is None:
        token = TOKENS.get(chain_id, {}).get(token_address)

    return token if token else tokens.UNKNOWN_TOKEN


def get_encoded_network_definition(
    chain_id: int | None = None,
    slip44: int | None = None,
) -> bytes | None:
    if not ((chain_id is None) != (slip44 is None)):  # not XOR
        raise ValueError(
            "Exactly one of chain_id or slip44 parameters are needed to construct network definition path."
        )

    path = ""

    if chain_id is not None:
        path = "/".join([FIXTURES_DEFINITIONS_DIR, DEFS_NETWORK_BY_CHAINID_LOOKUP_TYPE, str(chain_id),DEFS_NETWORK_URI_NAME])
    else:
        path = "/".join([FIXTURES_DEFINITIONS_DIR, DEFS_NETWORK_BY_SLIP44_LOOKUP_TYPE, str(slip44), DEFS_NETWORK_URI_NAME])

    return _get_definition_from_path(path)


def get_encoded_token_definition(
    chain_id: int = None,
    token_address: str = None,
) -> bytes | None:
    if chain_id is None or token_address is None:
        raise ValueError(
            "Both chain_id and token_address parameters are needed to construct token definition path."
        )

    addr = token_address.lower()
    if addr.startswith("0x"):
        addr = addr[2:]

    path = "/".join([FIXTURES_DEFINITIONS_DIR, DEFS_NETWORK_BY_CHAINID_LOOKUP_TYPE, str(chain_id), DEFS_TOKEN_URI_NAME.format(hex_address=addr)])
    return _get_definition_from_path(path)


def _get_definition_from_path(
    path: str,
) -> bytes | None:
    try:
        with uio.open(path, mode="rb") as f:
            b = f.read()
            return b
    except OSError:
        return None
