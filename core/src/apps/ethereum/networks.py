# generated from networks.py.mako
# (by running `make templates` in `core`)
# do not edit manually!

# NOTE: using positional arguments saves 4400 bytes in flash size,
# returning tuples instead of classes saved 800 bytes

from typing import TYPE_CHECKING

from trezor import utils
from trezor.messages import EthereumNetworkInfo

if TYPE_CHECKING:
    from typing import Iterator

    # Removing the necessity to construct object to save space
    # fmt: off
    NetworkInfoTuple = tuple[
        int,  # chain_id
        int,  # slip44
        str,  # symbol
        str,  # name
    ]
    # fmt: on

UNKNOWN_NETWORK = EthereumNetworkInfo(
    chain_id=0,
    slip44=0,
    symbol="UNKN",
    name="Unknown network",
)


def by_chain_id(chain_id: int) -> EthereumNetworkInfo:
    for n in _networks_iterator():
        n_chain_id = n[0]
        if n_chain_id == chain_id:
            return EthereumNetworkInfo(
                chain_id=n[0],
                slip44=n[1],
                symbol=n[2],
                name=n[3],
            )
    return UNKNOWN_NETWORK


def by_slip44(slip44: int) -> EthereumNetworkInfo:
    for n in _networks_iterator():
        n_slip44 = n[1]
        if n_slip44 == slip44:
            return EthereumNetworkInfo(
                chain_id=n[0],
                slip44=n[1],
                symbol=n[2],
                name=n[3],
            )
    return UNKNOWN_NETWORK


# fmt: off
def _networks_iterator() -> Iterator[NetworkInfoTuple]:
    if utils.INTERNAL_MODEL == "T2B1":
        yield (
            1,  # chain_id
            60,  # slip44
            "ETH",  # symbol
            "Ethereum",  # name
        )
        yield (
            10,  # chain_id
            614,  # slip44
            "ETH",  # symbol
            "Optimism",  # name
        )
        yield (
            56,  # chain_id
            714,  # slip44
            "BNB",  # symbol
            "BNB Smart Chain",  # name
        )
        yield (
            61,  # chain_id
            61,  # slip44
            "ETC",  # symbol
            "Ethereum Classic",  # name
        )
        yield (
            137,  # chain_id
            966,  # slip44
            "POL",  # symbol
            "Polygon",  # name
        )
        yield (
            8453,  # chain_id
            8453,  # slip44
            "ETH",  # symbol
            "Base",  # name
        )
        yield (
            17000,  # chain_id
            1,  # slip44
            "tHOL",  # symbol
            "Holesky",  # name
        )
        yield (
            42161,  # chain_id
            9001,  # slip44
            "ETH",  # symbol
            "Arbitrum One",  # name
        )
        yield (
            11155111,  # chain_id
            1,  # slip44
            "tSEP",  # symbol
            "Sepolia",  # name
        )
    if utils.INTERNAL_MODEL == "T2T1":
        yield (
            1,  # chain_id
            60,  # slip44
            "ETH",  # symbol
            "Ethereum",  # name
        )
        yield (
            10,  # chain_id
            614,  # slip44
            "ETH",  # symbol
            "Optimism",  # name
        )
        yield (
            56,  # chain_id
            714,  # slip44
            "BNB",  # symbol
            "BNB Smart Chain",  # name
        )
        yield (
            61,  # chain_id
            61,  # slip44
            "ETC",  # symbol
            "Ethereum Classic",  # name
        )
        yield (
            137,  # chain_id
            966,  # slip44
            "POL",  # symbol
            "Polygon",  # name
        )
        yield (
            8453,  # chain_id
            8453,  # slip44
            "ETH",  # symbol
            "Base",  # name
        )
        yield (
            17000,  # chain_id
            1,  # slip44
            "tHOL",  # symbol
            "Holesky",  # name
        )
        yield (
            42161,  # chain_id
            9001,  # slip44
            "ETH",  # symbol
            "Arbitrum One",  # name
        )
        yield (
            11155111,  # chain_id
            1,  # slip44
            "tSEP",  # symbol
            "Sepolia",  # name
        )
    if utils.INTERNAL_MODEL == "T3B1":
        yield (
            1,  # chain_id
            60,  # slip44
            "ETH",  # symbol
            "Ethereum",  # name
        )
        yield (
            10,  # chain_id
            614,  # slip44
            "ETH",  # symbol
            "Optimism",  # name
        )
        yield (
            56,  # chain_id
            714,  # slip44
            "BNB",  # symbol
            "BNB Smart Chain",  # name
        )
        yield (
            61,  # chain_id
            61,  # slip44
            "ETC",  # symbol
            "Ethereum Classic",  # name
        )
        yield (
            137,  # chain_id
            966,  # slip44
            "POL",  # symbol
            "Polygon",  # name
        )
        yield (
            8453,  # chain_id
            8453,  # slip44
            "ETH",  # symbol
            "Base",  # name
        )
        yield (
            17000,  # chain_id
            1,  # slip44
            "tHOL",  # symbol
            "Holesky",  # name
        )
        yield (
            42161,  # chain_id
            9001,  # slip44
            "ETH",  # symbol
            "Arbitrum One",  # name
        )
        yield (
            11155111,  # chain_id
            1,  # slip44
            "tSEP",  # symbol
            "Sepolia",  # name
        )
    if utils.INTERNAL_MODEL == "T3T1":
        yield (
            1,  # chain_id
            60,  # slip44
            "ETH",  # symbol
            "Ethereum",  # name
        )
        yield (
            10,  # chain_id
            614,  # slip44
            "ETH",  # symbol
            "Optimism",  # name
        )
        yield (
            56,  # chain_id
            714,  # slip44
            "BNB",  # symbol
            "BNB Smart Chain",  # name
        )
        yield (
            61,  # chain_id
            61,  # slip44
            "ETC",  # symbol
            "Ethereum Classic",  # name
        )
        yield (
            137,  # chain_id
            966,  # slip44
            "POL",  # symbol
            "Polygon",  # name
        )
        yield (
            8453,  # chain_id
            8453,  # slip44
            "ETH",  # symbol
            "Base",  # name
        )
        yield (
            17000,  # chain_id
            1,  # slip44
            "tHOL",  # symbol
            "Holesky",  # name
        )
        yield (
            42161,  # chain_id
            9001,  # slip44
            "ETH",  # symbol
            "Arbitrum One",  # name
        )
        yield (
            11155111,  # chain_id
            1,  # slip44
            "tSEP",  # symbol
            "Sepolia",  # name
        )
    if utils.INTERNAL_MODEL == "T3W1":
        yield (
            1,  # chain_id
            60,  # slip44
            "ETH",  # symbol
            "Ethereum",  # name
        )
        yield (
            10,  # chain_id
            614,  # slip44
            "ETH",  # symbol
            "Optimism",  # name
        )
        yield (
            56,  # chain_id
            714,  # slip44
            "BNB",  # symbol
            "BNB Smart Chain",  # name
        )
        yield (
            61,  # chain_id
            61,  # slip44
            "ETC",  # symbol
            "Ethereum Classic",  # name
        )
        yield (
            137,  # chain_id
            966,  # slip44
            "POL",  # symbol
            "Polygon",  # name
        )
        yield (
            8453,  # chain_id
            8453,  # slip44
            "ETH",  # symbol
            "Base",  # name
        )
        yield (
            17000,  # chain_id
            1,  # slip44
            "tHOL",  # symbol
            "Holesky",  # name
        )
        yield (
            42161,  # chain_id
            9001,  # slip44
            "ETH",  # symbol
            "Arbitrum One",  # name
        )
        yield (
            11155111,  # chain_id
            1,  # slip44
            "tSEP",  # symbol
            "Sepolia",  # name
        )
