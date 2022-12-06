# generated from networks.py.mako
# (by running `make templates` in `core`)
# do not edit manually!

# NOTE: using positional arguments saves 4400 bytes in flash size,
# returning tuples instead of classes saved 800 bytes

from typing import TYPE_CHECKING

from trezor.messages import EthereumNetworkInfo

from apps.common.paths import HARDENED

if TYPE_CHECKING:
    from typing import Iterator

    # Removing the necessity to construct object to save space
    # fmt: off
    NetworkInfoTuple = tuple[
        int,  # chain_id
        int,  # slip44
        str,  # shortcut
        str,  # name
    ]
    # fmt: on

UNKNOWN_NETWORK = EthereumNetworkInfo(
    chain_id=0,
    slip44=0,
    shortcut="UNKN",
    name="Unknown network",
)


def by_chain_id(chain_id: int) -> EthereumNetworkInfo | None:
    for n in _networks_iterator():
        n_chain_id = n[0]
        if n_chain_id == chain_id:
            return EthereumNetworkInfo(
                chain_id=n[0],
                slip44=n[1],
                shortcut=n[2],
                name=n[3],
            )
    return None


def by_slip44(slip44: int) -> EthereumNetworkInfo | None:
    for n in _networks_iterator():
        n_slip44 = n[1]
        if n_slip44 == slip44:
            return EthereumNetworkInfo(
                chain_id=n[0],
                slip44=n[1],
                shortcut=n[2],
                name=n[3],
            )
    return None


def all_slip44_ids_hardened() -> Iterator[int]:
    for n in _networks_iterator():
        # n_slip_44 is the second element
        yield n[1] | HARDENED


# fmt: off
def _networks_iterator() -> Iterator[NetworkInfoTuple]:
    yield (
        1,  # chain_id
        60,  # slip44
        "ETH",  # shortcut
        "Ethereum",  # name
    )
    yield (
        3,  # chain_id
        1,  # slip44
        "tROP",  # shortcut
        "Ropsten",  # name
    )
    yield (
        4,  # chain_id
        1,  # slip44
        "tRIN",  # shortcut
        "Rinkeby",  # name
    )
    yield (
        5,  # chain_id
        1,  # slip44
        "tGOR",  # shortcut
        "Görli",  # name
    )
    yield (
        56,  # chain_id
        714,  # slip44
        "BNB",  # shortcut
        "Binance Smart Chain",  # name
    )
    yield (
        61,  # chain_id
        61,  # slip44
        "ETC",  # shortcut
        "Ethereum Classic",  # name
    )
    yield (
        137,  # chain_id
        966,  # slip44
        "MATIC",  # shortcut
        "Polygon",  # name
    )
