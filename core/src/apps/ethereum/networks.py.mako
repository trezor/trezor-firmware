# generated from networks.py.mako
# (by running `make templates` in `core`)
# do not edit manually!

# NOTE: using positional arguments saves 4400 bytes in flash size,
# returning tuples instead of classes saved 800 bytes

from typing import TYPE_CHECKING

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
        bool  # rskip60
    ]
    # fmt: on


def shortcut_by_chain_id(chain_id: int) -> str:
    n = by_chain_id(chain_id)
    return n.shortcut if n is not None else "UNKN"


def by_chain_id(chain_id: int) -> "NetworkInfo" | None:
    for n in _networks_iterator():
        n_chain_id = n[0]
        if n_chain_id == chain_id:
            return NetworkInfo(
                chain_id=n[0],
                slip44=n[1],
                shortcut=n[2],
                name=n[3],
                rskip60=n[4],
            )
    return None


def by_slip44(slip44: int) -> "NetworkInfo" | None:
    for n in _networks_iterator():
        n_slip44 = n[1]
        if n_slip44 == slip44:
            return NetworkInfo(
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


class NetworkInfo:
    def __init__(
        self, chain_id: int, slip44: int, shortcut: str, name: str, rskip60: bool
    ) -> None:
        self.chain_id = chain_id
        self.slip44 = slip44
        self.shortcut = shortcut
        self.name = name
        self.rskip60 = rskip60


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
