# generated from networks.py.mako
# do not edit manually!

from micropython import const

from apps.common import HARDENED

SLIP44_WANCHAIN = const(5718350)
SLIP44_ETHEREUM = const(60)

if False:
    from typing import Iterator, Optional


def is_wanchain(chain_id: int, tx_type: int) -> bool:
    return tx_type in (1, 6) and chain_id in (1, 3)


def shortcut_by_chain_id(chain_id: int, tx_type: int = None) -> str:
    if is_wanchain(chain_id, tx_type):
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
    if slip44 == SLIP44_WANCHAIN:
        # Coerce to Ethereum
        slip44 = SLIP44_ETHEREUM
    for n in NETWORKS:
        if n.slip44 == slip44:
            return n
    return None


def all_slip44_ids_hardened() -> Iterator[int]:
    for n in NETWORKS:
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
NETWORKS = [
    NetworkInfo(
        chain_id=1,
        slip44=60,
        shortcut="ETH",
        name="Ethereum",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=2,
        slip44=40,
        shortcut="EXP",
        name="Expanse",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=3,
        slip44=1,
        shortcut="tROP",
        name="Ethereum Testnet Ropsten",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=4,
        slip44=1,
        shortcut="tRIN",
        name="Ethereum Testnet Rinkeby",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=5,
        slip44=1,
        shortcut="tGOR",
        name="Ethereum Testnet Goerli",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=8,
        slip44=108,
        shortcut="UBQ",
        name="Ubiq",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=11,
        slip44=916,
        shortcut="META",
        name="Metadium",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=28,
        slip44=1128,
        shortcut="ETSC",
        name="Ethereum Social",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=30,
        slip44=137,
        shortcut="RBTC",
        name="RSK",
        rskip60=True,
    ),
    NetworkInfo(
        chain_id=31,
        slip44=37310,
        shortcut="tRBTC",
        name="RSK Testnet",
        rskip60=True,
    ),
    NetworkInfo(
        chain_id=42,
        slip44=1,
        shortcut="tKOV",
        name="Ethereum Testnet Kovan",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=60,
        slip44=6060,
        shortcut="GO",
        name="GoChain",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=61,
        slip44=61,
        shortcut="ETC",
        name="Ethereum Classic",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=62,
        slip44=1,
        shortcut="tETC",
        name="Ethereum Classic Testnet",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=64,
        slip44=163,
        shortcut="ELLA",
        name="Ellaism",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=76,
        slip44=76,
        shortcut="MIX",
        name="Mix",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=101,
        slip44=464,
        shortcut="ETI",
        name="EtherInc",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=222,
        slip44=2221,
        shortcut="ASK",
        name="Permission",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=237,
        slip44=237,
        shortcut="DXN",
        name="DEXON",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=269,
        slip44=269,
        shortcut="HPB",
        name="High Performance Blockchain",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=466,
        slip44=466,
        shortcut="ERE",
        name="EtherCore",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=820,
        slip44=820,
        shortcut="CLO",
        name="Callisto",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=1620,
        slip44=1620,
        shortcut="ATH",
        name="Atheios",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=1987,
        slip44=1987,
        shortcut="EGEM",
        name="EtherGem",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=2018,
        slip44=2018,
        shortcut="EOSC",
        name="EOS Classic",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=2894,
        slip44=2894,
        shortcut="REOSC",
        name="REOSC Ecosystem",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=31102,
        slip44=31102,
        shortcut="ESN",
        name="Ethersocial Network",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=33416,
        slip44=33416,
        shortcut="TEO",
        name="Trust ETH reOrigin",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=200625,
        slip44=200625,
        shortcut="AKA",
        name="Akroma",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=246529,
        slip44=246529,
        shortcut="ATS",
        name="ARTIS sigma1",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=246785,
        slip44=1,
        shortcut="tATS",
        name="ARTIS tau1",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=1313114,
        slip44=1313114,
        shortcut="ETHO",
        name="Ether-1",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=7762959,
        slip44=184,
        shortcut="MUSIC",
        name="Musicoin",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=28945486,
        slip44=344,
        shortcut="AUX",
        name="Auxilium",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=61717561,
        slip44=61717561,
        shortcut="AQUA",
        name="Aquachain",
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=3125659152,
        slip44=164,
        shortcut="PIRL",
        name="Pirl",
        rskip60=False,
    ),
]
