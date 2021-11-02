# generated from networks.py.mako
# do not edit manually!

from apps.common.paths import HARDENED

if False:
    from typing import Iterator


def shortcut_by_chain_id(chain_id: int) -> str:
    n = by_chain_id(chain_id)
    return n.shortcut if n is not None else "UNKN"


def by_chain_id(chain_id: int) -> "NetworkInfo" | None:
    for n in _networks_iterator():
        if n.chain_id == chain_id:
            return n
    return None


def by_slip44(slip44: int) -> "NetworkInfo" | None:
    for n in _networks_iterator():
        if n.slip44 == slip44:
            return n
    return None


def all_slip44_ids_hardened() -> Iterator[int]:
    for n in _networks_iterator():
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
def _networks_iterator() -> Iterator[NetworkInfo]:
    yield NetworkInfo(
        chain_id=1,
        slip44=60,
        shortcut="ETH",
        name="Ethereum",
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
        name="Ubiq",
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
        chain_id=10,
        slip44=60,
        shortcut="OETH",
        name="Optimistic Ethereum",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=11,
        slip44=916,
        shortcut="META",
        name="Metadium",
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
        shortcut="tsDIODE",
        name="Diode Testnet Staging",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=14,
        slip44=60,
        shortcut="FLR",
        name="Flare",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=15,
        slip44=60,
        shortcut="DIODE",
        name="Diode Prenet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=16,
        slip44=1,
        shortcut="tCFLR",
        name="Flare Testnet Coston",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=17,
        slip44=60,
        shortcut="TFI",
        name="ThaiChain 2.0 ThaiFi",
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
        chain_id=19,
        slip44=60,
        shortcut="SGB",
        name="Songbird Canary-Network",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=20,
        slip44=60,
        shortcut="ELA",
        name="ELA-ETH-Sidechain",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=30,
        slip44=137,
        shortcut="RBTC",
        name="RSK",
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
        chain_id=33,
        slip44=60,
        shortcut="GooD",
        name="GoodData",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=35,
        slip44=60,
        shortcut="TBG",
        name="TBWG Chain",
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
        chain_id=40,
        slip44=60,
        shortcut="TLOS",
        name="Telos EVM",
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
        chain_id=44,
        slip44=60,
        shortcut="CRING",
        name="Darwinia Crab Network",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=50,
        slip44=60,
        shortcut="XDC",
        name="XinFin Network",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=51,
        slip44=1,
        shortcut="TXDC",
        name="XinFin Apothem Testnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=52,
        slip44=60,
        shortcut="cet",
        name="CoinEx Smart Chain",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=55,
        slip44=60,
        shortcut="ZYX",
        name="Zyx",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=56,
        slip44=714,
        shortcut="BNB",
        name="Binance Smart Chain",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=58,
        slip44=60,
        shortcut="ONG",
        name="Ontology",
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
        name="Ethereum Classic",
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
        chain_id=66,
        slip44=60,
        shortcut="OKT",
        name="OKExChain",
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
        chain_id=68,
        slip44=60,
        shortcut="SOTER",
        name="SoterOne",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=69,
        slip44=1,
        shortcut="tKOR",
        name="Optimistic Ethereum Testnet Kovan",
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
        chain_id=78,
        slip44=60,
        shortcut="PETH",
        name="PrimusChain",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=80,
        slip44=60,
        shortcut="RNA",
        name="GeneChain",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=82,
        slip44=60,
        shortcut="MTR",
        name="Meter",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=86,
        slip44=60,
        shortcut="GT",
        name="GateChain",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=88,
        slip44=889,
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
        slip44=178,
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
        chain_id=106,
        slip44=60,
        shortcut="VLX",
        name="Velas EVM",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=108,
        slip44=1001,
        shortcut="TT",
        name="ThunderCore",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=111,
        slip44=60,
        shortcut="ETL",
        name="EtherLite Chain",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=122,
        slip44=60,
        shortcut="FUSE",
        name="Fuse",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=124,
        slip44=60,
        shortcut="DWU",
        name="Decentralized Web",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=127,
        slip44=127,
        shortcut="FETH",
        name="Factory 127",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=128,
        slip44=1010,
        shortcut="HT",
        name="Huobi ECO Chain",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=137,
        slip44=966,
        shortcut="MATIC",
        name="Polygon",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=142,
        slip44=60,
        shortcut="DAX",
        name="DAX CHAIN",
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
        name="Lightstreams",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=199,
        slip44=60,
        shortcut="BTT",
        name="BitTorrent Chain",
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
        chain_id=222,
        slip44=2221,
        shortcut="ASK",
        name="Permission",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=246,
        slip44=246,
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
        chain_id=256,
        slip44=1,
        shortcut="thtt",
        name="Huobi ECO Chain Testnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=262,
        slip44=60,
        shortcut="SRN",
        name="SUR Blockchain Network",
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
        chain_id=321,
        slip44=60,
        shortcut="KCS",
        name="KCC",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=336,
        slip44=60,
        shortcut="SDN",
        name="Shiden",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=361,
        slip44=60,
        shortcut="TFUEL",
        name="Theta",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=369,
        slip44=60,
        shortcut="PLS",
        name="PulseChain",
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
        slip44=1,
        shortcut="tGOR",
        name="Optimistic Ethereum Testnet Goerli",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=499,
        slip44=499,
        shortcut="RUPX",
        name="Rupaya",
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
        chain_id=595,
        slip44=1,
        shortcut="tmACA",
        name="Acala Mandala Testnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=686,
        slip44=686,
        shortcut="KAR",
        name="Karura Network",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=777,
        slip44=60,
        shortcut="cTH",
        name="cheapETH",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=787,
        slip44=787,
        shortcut="ACA",
        name="Acala Network",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=803,
        slip44=60,
        shortcut="HAIC",
        name="Haic",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=820,
        slip44=820,
        shortcut="CLO",
        name="Callisto",
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
        chain_id=880,
        slip44=60,
        shortcut="AMBR",
        name="Ambros Chain",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=888,
        slip44=5718350,
        shortcut="WAN",
        name="Wanchain",
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
        chain_id=998,
        slip44=60,
        shortcut="L99",
        name="Lucky Network",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=1001,
        slip44=1,
        shortcut="tKLAY",
        name="Klaytn Testnet Baobab",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=1007,
        slip44=1,
        shortcut="tNEW",
        name="Newton Testnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=1010,
        slip44=1020,
        shortcut="EVC",
        name="Evrice Network",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=1012,
        slip44=60,
        shortcut="NEW",
        name="Newton",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=1022,
        slip44=60,
        shortcut="SKU",
        name="Sakura",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=1024,
        slip44=60,
        shortcut="CLV",
        name="Clover",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=1139,
        slip44=60,
        shortcut="MATH",
        name="MathChain",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=1140,
        slip44=1,
        shortcut="tMATH",
        name="MathChain Testnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=1213,
        slip44=60,
        shortcut="POP",
        name="Popcateum",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=1284,
        slip44=60,
        shortcut="GLMR",
        name="Moonbeam",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=1285,
        slip44=60,
        shortcut="MOVR",
        name="Moonriver",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=1286,
        slip44=60,
        shortcut="ROC",
        name="Moonrock",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=1287,
        slip44=60,
        shortcut="DEV",
        name="Moonbase Alpha",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=1288,
        slip44=60,
        shortcut="MSHD",
        name="Moonshadow",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=1618,
        slip44=60,
        shortcut="CATE",
        name="Catecoin Chain",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=1657,
        slip44=60,
        shortcut="BTA",
        name="Btachain",
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
        chain_id=2020,
        slip44=60,
        shortcut="420",
        name="420coin",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=2021,
        slip44=60,
        shortcut="EDG",
        name="Edgeware",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=2100,
        slip44=60,
        shortcut="ECO",
        name="Ecoball",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=2559,
        slip44=60,
        shortcut="KTO",
        name="Kortho",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=4689,
        slip44=60,
        shortcut="IOTX",
        name="IoTeX Network",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=5197,
        slip44=60,
        shortcut="ES",
        name="EraSwap",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=5869,
        slip44=60,
        shortcut="RBD",
        name="Wegochain Rubidium",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=8217,
        slip44=8217,
        shortcut="KLAY",
        name="Klaytn",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=8723,
        slip44=479,
        shortcut="OLO",
        name="TOOL Global",
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
        chain_id=10101,
        slip44=60,
        shortcut="GEN",
        name="Blockchain Genesis",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=16000,
        slip44=60,
        shortcut="MTT",
        name="MetaDot",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=24484,
        slip44=227,
        shortcut="WEB",
        name="Webchain",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=24734,
        slip44=60,
        shortcut="MINTME",
        name="MintMe.com Coin",
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
        chain_id=32659,
        slip44=60,
        shortcut="FSN",
        name="Fusion",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=39797,
        slip44=39797,
        shortcut="NRG",
        name="Energi",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=42069,
        slip44=60,
        shortcut="peggle",
        name="pegglecoin",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=42220,
        slip44=60,
        shortcut="CELO",
        name="Celo",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=43113,
        slip44=1,
        shortcut="tAVAX",
        name="Avalanche Fuji Testnet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=43114,
        slip44=9000,
        shortcut="AVAX",
        name="Avalanche",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=44787,
        slip44=1,
        shortcut="tCELO",
        name="Celo Alfajores Testnet",
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
        chain_id=62320,
        slip44=1,
        shortcut="tCELO",
        name="Celo Baklava Testnet",
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
        name="Polygon Testnet Mumbai",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=100000,
        slip44=60,
        shortcut="QKC",
        name="QuarkChain",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=100001,
        slip44=60,
        shortcut="QKC",
        name="QuarkChain",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=100002,
        slip44=60,
        shortcut="QKC",
        name="QuarkChain",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=100003,
        slip44=60,
        shortcut="QKC",
        name="QuarkChain",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=100004,
        slip44=60,
        shortcut="QKC",
        name="QuarkChain",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=100005,
        slip44=60,
        shortcut="QKC",
        name="QuarkChain",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=100006,
        slip44=60,
        shortcut="QKC",
        name="QuarkChain",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=100007,
        slip44=60,
        shortcut="QKC",
        name="QuarkChain",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=100008,
        slip44=60,
        shortcut="QKC",
        name="QuarkChain",
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
        chain_id=955305,
        slip44=1011,
        shortcut="ELV",
        name="Eluvio Content Fabric",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=1313114,
        slip44=1313114,
        shortcut="ETHO",
        name="Etho Protocol",
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
        chain_id=20181205,
        slip44=60,
        shortcut="QKI",
        name="quarkblockchain",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=28945486,
        slip44=344,
        shortcut="AUX",
        name="Auxilium Network",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=35855456,
        slip44=60,
        shortcut="JOYS",
        name="Joys Digital",
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
        chain_id=99415706,
        slip44=1,
        shortcut="TOYS",
        name="Joys Digital TestNet",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=245022934,
        slip44=60,
        shortcut="NEON",
        name="Neon EVM",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=311752642,
        slip44=60,
        shortcut="OLT",
        name="OneLedger",
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
        shortcut="aETH",
        name="Aurora",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=1666600000,
        slip44=60,
        shortcut="ONE",
        name="Harmony",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=1666600001,
        slip44=60,
        shortcut="ONE",
        name="Harmony",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=1666600002,
        slip44=60,
        shortcut="ONE",
        name="Harmony",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=1666600003,
        slip44=60,
        shortcut="ONE",
        name="Harmony",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=3125659152,
        slip44=164,
        shortcut="PIRL",
        name="Pirl",
        rskip60=False,
    )
    yield NetworkInfo(
        chain_id=11297108109,
        slip44=60,
        shortcut="PALM",
        name="Palm",
        rskip60=False,
    )
