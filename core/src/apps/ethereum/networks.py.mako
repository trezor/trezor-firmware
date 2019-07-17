# generated from networks.py.mako
# do not edit manually!

from apps.common import HARDENED

if False:
    from typing import Iterator, Optional


def shortcut_by_chain_id(chain_id: int, tx_type: int = None) -> str:
    if tx_type in (1, 6) and chain_id in (1, 3):
        return "WAN"
    else:
        n = by_chain_id(chain_id)
        return n.shortcut if n is not None else "UNKN"


def by_chain_id(chain_id: int) -> Optional["NetworkInfo"]:
    for n in NETWORKS:
        if n.chain_id == chain_id:
            return n
    return None


def by_slip44(slip44: int) -> Optional["NetworkInfo"]:
    for n in NETWORKS:
        if n.slip44 == slip44:
            return n
    return None


def all_slip44_ids_hardened() -> Iterator[int]:
    for n in NETWORKS:
        yield n.slip44 | HARDENED


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
NETWORKS = [
% for n in supported_on("trezor2", eth):
    NetworkInfo(
        chain_id=${n.chain_id},
        slip44=${n.slip44},
        shortcut="${n.shortcut}",
        name="${n.name}",
        rskip60=${n.rskip60},
    ),
% endfor
]
