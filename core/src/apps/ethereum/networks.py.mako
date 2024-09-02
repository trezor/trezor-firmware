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
% for model in ALL_MODELS:
    if utils.INTERNAL_MODEL == "${model}":
% for n in sorted(supported_on(model, eth), key=lambda network: (int(network.chain_id), network.name)):
        yield (
            ${n.chain_id},  # chain_id
            ${n.slip44},  # slip44
            "${n.shortcut}",  # symbol
            "${n.name}",  # name
        )
% endfor
% endfor
