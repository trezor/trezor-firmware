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
    for n in _networks_iterator():
        if n.chain_id == chain_id:
            return n
    return None


def by_slip44(slip44: int) -> Optional["NetworkInfo"]:
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
    yield NetworkInfo(
        chain_id=1,
        slip44=60,
        shortcut="ETH",
        name="Ethereum Mainnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=2,
        slip44=40,
        shortcut="EXP",
        name="Expanse Network",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=3,
        slip44=1,
        shortcut="tROP",
        name="Ethereum Testnet Ropsten",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=4,
        slip44=1,
        shortcut="tRIN",
        name="Ethereum Testnet Rinkeby",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=5,
        slip44=1,
        shortcut="tGOR",
        name="Ethereum Testnet Görli",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=6,
        slip44=1,
        shortcut="tKOT",
        name="Ethereum Classic Testnet Kotti",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=7,
        slip44=60,
        shortcut="TCH",
        name="ThaiChain",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=8,
        slip44=108,
        shortcut="UBQ",
        name="Ubiq Network Mainnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=9,
        slip44=1,
        shortcut="TUBQ",
        name="Ubiq Network Testnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=11,
        slip44=916,
        shortcut="META",
        name="Metadium Mainnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=12,
        slip44=1,
        shortcut="tKAL",
        name="Metadium Testnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=13,
        slip44=1,
        shortcut="tsDIO",
        name="Diode Testnet Staging",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=15,
        slip44=60,
        shortcut="DIO",
        name="Diode Prenet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=18,
        slip44=1,
        shortcut="TST",
        name="ThunderCore Testnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=20,
        slip44=60,
        shortcut="ELA",
        name="ELA-ETH-Sidechain Mainnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=21,
        slip44=1,
        shortcut="tELA",
        name="ELA-ETH-Sidechain Testnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=30,
        slip44=137,
        shortcut="RBTC",
        name="RSK Mainnet",
        rskip60=True,
    )
    yield NetworkInfo(
        chain_id=31,
        slip44=1,
        shortcut="tRBTC",
        name="RSK Testnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=38,
        slip44=538,
        shortcut="VAL",
        name="Valorbit",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=42,
        slip44=1,
        shortcut="tKOV",
        name="Ethereum Testnet Kovan",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=56,
        slip44=60,
        shortcut="BNB",
        name="Binance Smart Chain Mainnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=60,
        slip44=6060,
        shortcut="GO",
        name="GoChain",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=61,
        slip44=61,
        shortcut="ETC",
        name="Ethereum Classic Mainnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=62,
        slip44=1,
        shortcut="TETC",
        name="Ethereum Classic Testnet Morden",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=63,
        slip44=1,
        shortcut="tMETC",
        name="Ethereum Classic Testnet Mordor",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=64,
        slip44=163,
        shortcut="ELLA",
        name="Ellaism",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=67,
        slip44=1,
        shortcut="tDBM",
        name="DBChain Testnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=76,
        slip44=76,
        shortcut="MIX",
        name="Mix",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=77,
        slip44=60,
        shortcut="POA",
        name="POA Network Sokol",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=88,
        slip44=60,
        shortcut="TOMO",
        name="TomoChain",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=97,
        slip44=1,
        shortcut="tBNB",
        name="Binance Smart Chain Testnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=99,
        slip44=60,
        shortcut="SKL",
        name="POA Network Core",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=100,
        slip44=700,
        shortcut="xDAI",
        name="xDAI Chain",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=101,
        slip44=464,
        shortcut="ETI",
        name="EtherInc",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=108,
        slip44=60,
        shortcut="TT",
        name="ThunderCore Mainnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=122,
        slip44=60,
        shortcut="FUSE",
        name="Fuse Mainnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=137,
        slip44=60,
        shortcut="MATIC",
        name="Matic Mainnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=162,
        slip44=1,
        shortcut="tPHT",
        name="Lightstreams Testnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=163,
        slip44=60,
        shortcut="PHT",
        name="Lightstreams Mainnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=211,
        slip44=60,
        shortcut="0xF",
        name="Freight Trust Network",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=246,
        slip44=60,
        shortcut="EWT",
        name="Energy Web Chain",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=250,
        slip44=60,
        shortcut="FTM",
        name="Fantom Opera",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=269,
        slip44=269,
        shortcut="HPB",
        name="High Performance Blockchain",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=385,
        slip44=60,
        shortcut="LISINSKI",
        name="Lisinski",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=420,
        slip44=60,
        shortcut="OETH",
        name="Optimistic Ethereum",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=558,
        slip44=60,
        shortcut="TAO",
        name="Tao Network",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=820,
        slip44=820,
        shortcut="CLO",
        name="Callisto Mainnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=821,
        slip44=1,
        shortcut="TCLO",
        name="Callisto Testnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=977,
        slip44=60,
        shortcut="YETI",
        name="Nepal Blockchain Network",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=1856,
        slip44=60,
        shortcut="TSF",
        name="Teslafunds",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=1987,
        slip44=1987,
        shortcut="EGEM",
        name="EtherGem",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=5869,
        slip44=60,
        shortcut="RBD",
        name="Wegochain Rubidium Mainnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=8995,
        slip44=60,
        shortcut="U+25B3",
        name="bloxberg",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=24484,
        slip44=60,
        shortcut="WEB",
        name="Webchain",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=31102,
        slip44=31102,
        shortcut="ESN",
        name="Ethersocial Network",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=39797,
        slip44=39797,
        shortcut="NRG",
        name="Energi Mainnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=49797,
        slip44=1,
        shortcut="tNRG",
        name="Energi Testnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=73799,
        slip44=1,
        shortcut="tVT",
        name="Energy Web Volta Testnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=78110,
        slip44=60,
        shortcut="FIN",
        name="Firenze test network",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=80001,
        slip44=1,
        shortcut="tMATIC",
        name="Matic Testnet Mumbai",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=200625,
        slip44=200625,
        shortcut="AKA",
        name="Akroma",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=246529,
        slip44=246529,
        shortcut="ATS",
        name="ARTIS sigma1",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=246785,
        slip44=1,
        shortcut="tATS",
        name="ARTIS Testnet tau1",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=1313114,
        slip44=1313114,
        shortcut="ETHO",
        name="Ether-1",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=1313500,
        slip44=60,
        shortcut="XERO",
        name="Xerom",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=7762959,
        slip44=184,
        shortcut="MUSIC",
        name="Musicoin",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=13371337,
        slip44=60,
        shortcut="TPEP",
        name="PepChain Churchill",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=18289463,
        slip44=60,
        shortcut="ILT",
        name="IOLite",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=28945486,
        slip44=344,
        shortcut="AUX",
        name="Auxilium Network Mainnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=61717561,
        slip44=61717561,
        shortcut="AQUA",
        name="Aquachain",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=1122334455,
        slip44=60,
        shortcut="IPOS",
        name="IPOS Network",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=1313161554,
        slip44=60,
        shortcut="NEAR",
        name="NEAR MainNet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=1313161555,
        slip44=1,
        shortcut="tNEAR",
        name="NEAR TestNet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=3125659152,
        slip44=164,
        shortcut="PIRL",
        name="Pirl",
        rskip60=False,
    )
