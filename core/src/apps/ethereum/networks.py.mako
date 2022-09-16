# generated from networks.py.mako
# (by running `make templates` in `core`)
# do not edit manually!

# NOTE: using positional arguments saves 4400 bytes in flash size,
# returning tuples instead of classes saved 800 bytes

from typing import TYPE_CHECKING

from apps.common.paths import HARDENED
from trezor.messages import EthereumNetworkInfo

if TYPE_CHECKING:
    from typing import Iterator

    # Removing the necessity to construct object to save space
    # fmt: off
    NetworkInfoTuple = tuple[
        int,  # chain_id
        int,  # slip44
        str,  # shortcut
        str,  # name
        bool  # rskip60
    ]
    # fmt: on
UNKNOWN_NETWORK_SHORTCUT = "UNKN"


def by_chain_id(chain_id: int) -> EthereumNetworkInfo | None:
    for n in _networks_iterator():
        n_chain_id = n[0]
        if n_chain_id == chain_id:
            return EthereumNetworkInfo(
                chain_id=n[0],
                slip44=n[1],
                shortcut=n[2],
                name=n[3],
                rskip60=n[4],
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
                rskip60=n[4],
            )
    return None


def all_slip44_ids_hardened() -> Iterator[int]:
    for n in _networks_iterator():
        # n_slip_44 is the second element
        yield n[1] | HARDENED


# fmt: off
def _networks_iterator() -> Iterator[NetworkInfoTuple]:
% for n in supported_on("trezor2", eth):
    yield (
        ${n.chain_id},  # chain_id
        ${n.slip44},  # slip44
        "${n.shortcut}",  # shortcut
        "${n.name}",  # name
        ${n.rskip60},  # rskip60
    )
% endfor
