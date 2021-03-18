# generated from networks.py.mako
# do not edit manually!

from micropython import const

from apps.common import HARDENED

SLIP44_WANCHAIN = const(5718350)
SLIP44_ETHEREUM = const(60)

if False:
    from typing import Iterator


def is_wanchain(chain_id: int, tx_type: int) -> bool:
    return tx_type in (1, 6) and chain_id in (1, 3)


def shortcut_by_chain_id(chain_id: int, tx_type: int = None) -> str:
    if is_wanchain(chain_id, tx_type):
        return "WAN"
    else:
        n = by_chain_id(chain_id)
        return n.shortcut if n is not None else "UNKN"


def by_chain_id(chain_id: int) -> "NetworkInfo" | None:
    for n in _networks_iterator():
        if n.chain_id == chain_id:
            return n
    return None


def by_slip44(slip44: int) -> "NetworkInfo" | None:
    if slip44 == SLIP44_WANCHAIN:
        # Coerce to Ethereum
        slip44 = SLIP44_ETHEREUM
    for n in _networks_iterator():
        if n.slip44 == slip44:
            return n
    return None


def all_slip44_ids_hardened() -> Iterator[int]:
    for n in _networks_iterator():
        yield n.slip44 | HARDENED
    yield SLIP44_WANCHAIN | HARDENED


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
def _networks_iterator() -> Iterator[NetworkInfo]:
% for n in supported_on("trezor2", eth):
    yield NetworkInfo(
        chain_id=${n.chain_id},
        slip44=${n.slip44},
        shortcut="${n.shortcut}",
        name="${n.name}",
        rskip60=${n.rskip60},
    )
% endfor
