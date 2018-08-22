# generated from networks.py.mako
# do not edit manually!


def shortcut_by_chain_id(chain_id, tx_type=None):
    if tx_type in [1, 6] and chain_id in [1, 3]:
        return "WAN"
    else:
        n = by_chain_id(chain_id)
        return n.shortcut if n is not None else "UNKN"


def by_chain_id(chain_id):
    for n in NETWORKS:
        if n.chain_id == chain_id:
            return n
    return None


def by_slip44(slip44):
    for n in NETWORKS:
        if n.slip44 == slip44:
            return n
    return None


class NetworkInfo:
    def __init__(
        self, chain_id: int, slip44: int, shortcut: str, name: str, rskip60: bool
    ):
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
