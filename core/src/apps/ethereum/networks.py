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
    yield (
        1,  # chain_id
        60,  # slip44
        "ETH",  # shortcut
        "Ethereum",  # name
        False,  # rskip60
    )
    yield (
        2,  # chain_id
        40,  # slip44
        "EXP",  # shortcut
        "Expanse Network",  # name
        False,  # rskip60
    )
    yield (
        3,  # chain_id
        1,  # slip44
        "tROP",  # shortcut
        "Ropsten",  # name
        False,  # rskip60
    )
    yield (
        4,  # chain_id
        1,  # slip44
        "tRIN",  # shortcut
        "Rinkeby",  # name
        False,  # rskip60
    )
    yield (
        5,  # chain_id
        1,  # slip44
        "tGOR",  # shortcut
        "Görli",  # name
        False,  # rskip60
    )
    yield (
        6,  # chain_id
        1,  # slip44
        "tKOT",  # shortcut
        "Ethereum Classic Testnet Kotti",  # name
        False,  # rskip60
    )
    yield (
        7,  # chain_id
        60,  # slip44
        "TCH",  # shortcut
        "ThaiChain",  # name
        False,  # rskip60
    )
    yield (
        8,  # chain_id
        108,  # slip44
        "UBQ",  # shortcut
        "Ubiq",  # name
        False,  # rskip60
    )
    yield (
        9,  # chain_id
        1,  # slip44
        "TUBQ",  # shortcut
        "Ubiq Network Testnet",  # name
        False,  # rskip60
    )
    yield (
        11,  # chain_id
        916,  # slip44
        "META",  # shortcut
        "Metadium",  # name
        False,  # rskip60
    )
    yield (
        12,  # chain_id
        1,  # slip44
        "tKAL",  # shortcut
        "Metadium Testnet",  # name
        False,  # rskip60
    )
    yield (
        13,  # chain_id
        1,  # slip44
        "tsDIODE",  # shortcut
        "Diode Testnet Staging",  # name
        False,  # rskip60
    )
    yield (
        14,  # chain_id
        60,  # slip44
        "FLR",  # shortcut
        "Flare",  # name
        False,  # rskip60
    )
    yield (
        15,  # chain_id
        60,  # slip44
        "DIODE",  # shortcut
        "Diode Prenet",  # name
        False,  # rskip60
    )
    yield (
        16,  # chain_id
        1,  # slip44
        "tCFLR",  # shortcut
        "Flare Testnet Coston",  # name
        False,  # rskip60
    )
    yield (
        17,  # chain_id
        60,  # slip44
        "TFI",  # shortcut
        "ThaiChain 2.0 ThaiFi",  # name
        False,  # rskip60
    )
    yield (
        18,  # chain_id
        1,  # slip44
        "TST",  # shortcut
        "ThunderCore Testnet",  # name
        False,  # rskip60
    )
    yield (
        19,  # chain_id
        60,  # slip44
        "SGB",  # shortcut
        "Songbird Canary-Network",  # name
        False,  # rskip60
    )
    yield (
        20,  # chain_id
        60,  # slip44
        "ELA",  # shortcut
        "Elastos Smart Chain",  # name
        False,  # rskip60
    )
    yield (
        24,  # chain_id
        60,  # slip44
        "DTH",  # shortcut
        "Dithereum",  # name
        False,  # rskip60
    )
    yield (
        25,  # chain_id
        60,  # slip44
        "CRO",  # shortcut
        "Cronos",  # name
        False,  # rskip60
    )
    yield (
        27,  # chain_id
        60,  # slip44
        "SHIB",  # shortcut
        "ShibaChain",  # name
        False,  # rskip60
    )
    yield (
        29,  # chain_id
        60,  # slip44
        "L1",  # shortcut
        "Genesis L1",  # name
        False,  # rskip60
    )
    yield (
        30,  # chain_id
        137,  # slip44
        "RBTC",  # shortcut
        "RSK",  # name
        True,  # rskip60
    )
    yield (
        31,  # chain_id
        1,  # slip44
        "tRBTC",  # shortcut
        "RSK Testnet",  # name
        False,  # rskip60
    )
    yield (
        33,  # chain_id
        60,  # slip44
        "GooD",  # shortcut
        "GoodData",  # name
        False,  # rskip60
    )
    yield (
        35,  # chain_id
        60,  # slip44
        "TBG",  # shortcut
        "TBWG Chain",  # name
        False,  # rskip60
    )
    yield (
        36,  # chain_id
        60,  # slip44
        "DX",  # shortcut
        "Dxchain",  # name
        False,  # rskip60
    )
    yield (
        38,  # chain_id
        538,  # slip44
        "VAL",  # shortcut
        "Valorbit",  # name
        False,  # rskip60
    )
    yield (
        40,  # chain_id
        60,  # slip44
        "TLOS",  # shortcut
        "Telos EVM",  # name
        False,  # rskip60
    )
    yield (
        42,  # chain_id
        1,  # slip44
        "tKOV",  # shortcut
        "Kovan",  # name
        False,  # rskip60
    )
    yield (
        44,  # chain_id
        60,  # slip44
        "CRAB",  # shortcut
        "Darwinia Crab Network",  # name
        False,  # rskip60
    )
    yield (
        46,  # chain_id
        60,  # slip44
        "RING",  # shortcut
        "Darwinia Network",  # name
        False,  # rskip60
    )
    yield (
        50,  # chain_id
        60,  # slip44
        "XDC",  # shortcut
        "XinFin Network",  # name
        False,  # rskip60
    )
    yield (
        51,  # chain_id
        1,  # slip44
        "TXDC",  # shortcut
        "XinFin Apothem Testnet",  # name
        False,  # rskip60
    )
    yield (
        52,  # chain_id
        60,  # slip44
        "cet",  # shortcut
        "CoinEx Smart Chain",  # name
        False,  # rskip60
    )
    yield (
        54,  # chain_id
        60,  # slip44
        "BELLY",  # shortcut
        "Openpiece",  # name
        False,  # rskip60
    )
    yield (
        55,  # chain_id
        60,  # slip44
        "ZYX",  # shortcut
        "Zyx",  # name
        False,  # rskip60
    )
    yield (
        56,  # chain_id
        714,  # slip44
        "BNB",  # shortcut
        "Binance Smart Chain",  # name
        False,  # rskip60
    )
    yield (
        58,  # chain_id
        60,  # slip44
        "ONG",  # shortcut
        "Ontology",  # name
        False,  # rskip60
    )
    yield (
        60,  # chain_id
        6060,  # slip44
        "GO",  # shortcut
        "GoChain",  # name
        False,  # rskip60
    )
    yield (
        61,  # chain_id
        61,  # slip44
        "ETC",  # shortcut
        "Ethereum Classic",  # name
        False,  # rskip60
    )
    yield (
        62,  # chain_id
        1,  # slip44
        "TETC",  # shortcut
        "Ethereum Classic Testnet Morden",  # name
        False,  # rskip60
    )
    yield (
        63,  # chain_id
        1,  # slip44
        "tMETC",  # shortcut
        "Ethereum Classic Testnet Mordor",  # name
        False,  # rskip60
    )
    yield (
        66,  # chain_id
        60,  # slip44
        "OKT",  # shortcut
        "OKXChain",  # name
        False,  # rskip60
    )
    yield (
        67,  # chain_id
        1,  # slip44
        "tDBM",  # shortcut
        "DBChain Testnet",  # name
        False,  # rskip60
    )
    yield (
        68,  # chain_id
        60,  # slip44
        "SOTER",  # shortcut
        "SoterOne",  # name
        False,  # rskip60
    )
    yield (
        69,  # chain_id
        1,  # slip44
        "tKOR",  # shortcut
        "Optimism Kovan",  # name
        False,  # rskip60
    )
    yield (
        70,  # chain_id
        1170,  # slip44
        "HOO",  # shortcut
        "Hoo Smart Chain",  # name
        False,  # rskip60
    )
    yield (
        74,  # chain_id
        60,  # slip44
        "EIDI",  # shortcut
        "IDChain",  # name
        False,  # rskip60
    )
    yield (
        76,  # chain_id
        76,  # slip44
        "MIX",  # shortcut
        "Mix",  # name
        False,  # rskip60
    )
    yield (
        77,  # chain_id
        60,  # slip44
        "SPOA",  # shortcut
        "POA Network Sokol",  # name
        False,  # rskip60
    )
    yield (
        78,  # chain_id
        60,  # slip44
        "PETH",  # shortcut
        "PrimusChain",  # name
        False,  # rskip60
    )
    yield (
        79,  # chain_id
        60,  # slip44
        "ZENITH",  # shortcut
        "Zenith",  # name
        False,  # rskip60
    )
    yield (
        80,  # chain_id
        60,  # slip44
        "RNA",  # shortcut
        "GeneChain",  # name
        False,  # rskip60
    )
    yield (
        82,  # chain_id
        60,  # slip44
        "MTR",  # shortcut
        "Meter",  # name
        False,  # rskip60
    )
    yield (
        86,  # chain_id
        60,  # slip44
        "GT",  # shortcut
        "GateChain",  # name
        False,  # rskip60
    )
    yield (
        87,  # chain_id
        60,  # slip44
        "SNT",  # shortcut
        "Nova Network",  # name
        False,  # rskip60
    )
    yield (
        88,  # chain_id
        889,  # slip44
        "TOMO",  # shortcut
        "TomoChain",  # name
        False,  # rskip60
    )
    yield (
        90,  # chain_id
        60,  # slip44
        "GAR",  # shortcut
        "Garizon Stage0",  # name
        False,  # rskip60
    )
    yield (
        96,  # chain_id
        60,  # slip44
        "NEXT",  # shortcut
        "NEXT Smart Chain",  # name
        False,  # rskip60
    )
    yield (
        97,  # chain_id
        1,  # slip44
        "tBNB",  # shortcut
        "Binance Smart Chain Testnet",  # name
        False,  # rskip60
    )
    yield (
        99,  # chain_id
        178,  # slip44
        "POA",  # shortcut
        "POA Network Core",  # name
        False,  # rskip60
    )
    yield (
        100,  # chain_id
        700,  # slip44
        "xDAI",  # shortcut
        "Gnosis Chain",  # name
        False,  # rskip60
    )
    yield (
        101,  # chain_id
        464,  # slip44
        "ETI",  # shortcut
        "EtherInc",  # name
        False,  # rskip60
    )
    yield (
        105,  # chain_id
        60,  # slip44
        "W3G",  # shortcut
        "Web3Games Devnet",  # name
        False,  # rskip60
    )
    yield (
        106,  # chain_id
        60,  # slip44
        "VLX",  # shortcut
        "Velas EVM",  # name
        False,  # rskip60
    )
    yield (
        108,  # chain_id
        1001,  # slip44
        "TT",  # shortcut
        "ThunderCore",  # name
        False,  # rskip60
    )
    yield (
        111,  # chain_id
        60,  # slip44
        "ETL",  # shortcut
        "EtherLite Chain",  # name
        False,  # rskip60
    )
    yield (
        122,  # chain_id
        60,  # slip44
        "FUSE",  # shortcut
        "Fuse",  # name
        False,  # rskip60
    )
    yield (
        123,  # chain_id
        60,  # slip44
        "SPARK",  # shortcut
        "Fuse Sparknet",  # name
        False,  # rskip60
    )
    yield (
        124,  # chain_id
        60,  # slip44
        "DWU",  # shortcut
        "Decentralized Web",  # name
        False,  # rskip60
    )
    yield (
        126,  # chain_id
        126,  # slip44
        "OY",  # shortcut
        "OYchain",  # name
        False,  # rskip60
    )
    yield (
        127,  # chain_id
        127,  # slip44
        "FETH",  # shortcut
        "Factory 127",  # name
        False,  # rskip60
    )
    yield (
        128,  # chain_id
        1010,  # slip44
        "HT",  # shortcut
        "Huobi ECO Chain",  # name
        False,  # rskip60
    )
    yield (
        137,  # chain_id
        966,  # slip44
        "MATIC",  # shortcut
        "Polygon",  # name
        False,  # rskip60
    )
    yield (
        142,  # chain_id
        60,  # slip44
        "DAX",  # shortcut
        "DAX CHAIN",  # name
        False,  # rskip60
    )
    yield (
        162,  # chain_id
        1,  # slip44
        "tPHT",  # shortcut
        "Lightstreams Testnet",  # name
        False,  # rskip60
    )
    yield (
        163,  # chain_id
        60,  # slip44
        "PHT",  # shortcut
        "Lightstreams",  # name
        False,  # rskip60
    )
    yield (
        168,  # chain_id
        60,  # slip44
        "AIOZ",  # shortcut
        "AIOZ Network",  # name
        False,  # rskip60
    )
    yield (
        180,  # chain_id
        60,  # slip44
        "AME",  # shortcut
        "AME Chain",  # name
        False,  # rskip60
    )
    yield (
        186,  # chain_id
        60,  # slip44
        "Seele",  # shortcut
        "Seele",  # name
        False,  # rskip60
    )
    yield (
        188,  # chain_id
        60,  # slip44
        "BTM",  # shortcut
        "BMC",  # name
        False,  # rskip60
    )
    yield (
        193,  # chain_id
        60,  # slip44
        "CEM",  # shortcut
        "Crypto Emergency",  # name
        False,  # rskip60
    )
    yield (
        199,  # chain_id
        60,  # slip44
        "BTT",  # shortcut
        "BitTorrent Chain",  # name
        False,  # rskip60
    )
    yield (
        211,  # chain_id
        60,  # slip44
        "0xF",  # shortcut
        "Freight Trust Network",  # name
        False,  # rskip60
    )
    yield (
        222,  # chain_id
        2221,  # slip44
        "ASK",  # shortcut
        "Permission",  # name
        False,  # rskip60
    )
    yield (
        225,  # chain_id
        60,  # slip44
        "LA",  # shortcut
        "LACHAIN",  # name
        False,  # rskip60
    )
    yield (
        246,  # chain_id
        246,  # slip44
        "EWT",  # shortcut
        "Energy Web Chain",  # name
        False,  # rskip60
    )
    yield (
        250,  # chain_id
        60,  # slip44
        "FTM",  # shortcut
        "Fantom Opera",  # name
        False,  # rskip60
    )
    yield (
        256,  # chain_id
        1,  # slip44
        "thtt",  # shortcut
        "Huobi ECO Chain Testnet",  # name
        False,  # rskip60
    )
    yield (
        258,  # chain_id
        60,  # slip44
        "SETM",  # shortcut
        "Setheum",  # name
        False,  # rskip60
    )
    yield (
        262,  # chain_id
        60,  # slip44
        "SRN",  # shortcut
        "SUR Blockchain Network",  # name
        False,  # rskip60
    )
    yield (
        269,  # chain_id
        269,  # slip44
        "HPB",  # shortcut
        "High Performance Blockchain",  # name
        False,  # rskip60
    )
    yield (
        300,  # chain_id
        60,  # slip44
        "xDAI",  # shortcut
        "Optimism on Gnosis Chain",  # name
        False,  # rskip60
    )
    yield (
        321,  # chain_id
        60,  # slip44
        "KCS",  # shortcut
        "KCC",  # name
        False,  # rskip60
    )
    yield (
        333,  # chain_id
        60,  # slip44
        "W3Q",  # shortcut
        "Web3Q",  # name
        False,  # rskip60
    )
    yield (
        336,  # chain_id
        60,  # slip44
        "SDN",  # shortcut
        "Shiden",  # name
        False,  # rskip60
    )
    yield (
        369,  # chain_id
        60,  # slip44
        "PLS",  # shortcut
        "PulseChain",  # name
        False,  # rskip60
    )
    yield (
        385,  # chain_id
        60,  # slip44
        "LISINS",  # shortcut
        "Lisinski",  # name
        False,  # rskip60
    )
    yield (
        416,  # chain_id
        60,  # slip44
        "SX",  # shortcut
        "SX Network",  # name
        False,  # rskip60
    )
    yield (
        499,  # chain_id
        499,  # slip44
        "RUPX",  # shortcut
        "Rupaya",  # name
        False,  # rskip60
    )
    yield (
        512,  # chain_id
        1512,  # slip44
        "AAC",  # shortcut
        "Double-A Chain",  # name
        False,  # rskip60
    )
    yield (
        520,  # chain_id
        60,  # slip44
        "XT",  # shortcut
        "XT Smart Chain",  # name
        False,  # rskip60
    )
    yield (
        530,  # chain_id
        60,  # slip44
        "FX",  # shortcut
        "F(x)Core",  # name
        False,  # rskip60
    )
    yield (
        534,  # chain_id
        674,  # slip44
        "CNDL",  # shortcut
        "Candle",  # name
        False,  # rskip60
    )
    yield (
        555,  # chain_id
        60,  # slip44
        "CLASS",  # shortcut
        "Vela1 Chain",  # name
        False,  # rskip60
    )
    yield (
        558,  # chain_id
        60,  # slip44
        "TAO",  # shortcut
        "Tao Network",  # name
        False,  # rskip60
    )
    yield (
        592,  # chain_id
        60,  # slip44
        "ASTR",  # shortcut
        "Astar",  # name
        False,  # rskip60
    )
    yield (
        595,  # chain_id
        1,  # slip44
        "tmACA",  # shortcut
        "Acala Mandala Testnet",  # name
        False,  # rskip60
    )
    yield (
        686,  # chain_id
        686,  # slip44
        "KAR",  # shortcut
        "Karura Network",  # name
        False,  # rskip60
    )
    yield (
        707,  # chain_id
        60,  # slip44
        "BCS",  # shortcut
        "BlockChain Station",  # name
        False,  # rskip60
    )
    yield (
        777,  # chain_id
        60,  # slip44
        "cTH",  # shortcut
        "cheapETH",  # name
        False,  # rskip60
    )
    yield (
        787,  # chain_id
        787,  # slip44
        "ACA",  # shortcut
        "Acala Network",  # name
        False,  # rskip60
    )
    yield (
        803,  # chain_id
        60,  # slip44
        "HAIC",  # shortcut
        "Haic",  # name
        False,  # rskip60
    )
    yield (
        820,  # chain_id
        820,  # slip44
        "CLO",  # shortcut
        "Callisto",  # name
        False,  # rskip60
    )
    yield (
        821,  # chain_id
        1,  # slip44
        "TCLO",  # shortcut
        "Callisto Testnet",  # name
        False,  # rskip60
    )
    yield (
        880,  # chain_id
        60,  # slip44
        "AMBROS",  # shortcut
        "Ambros Chain",  # name
        False,  # rskip60
    )
    yield (
        888,  # chain_id
        5718350,  # slip44
        "WAN",  # shortcut
        "Wanchain",  # name
        False,  # rskip60
    )
    yield (
        909,  # chain_id
        60,  # slip44
        "PFT",  # shortcut
        "Portal Fantasy Chain",  # name
        False,  # rskip60
    )
    yield (
        977,  # chain_id
        60,  # slip44
        "YETI",  # shortcut
        "Nepal Blockchain Network",  # name
        False,  # rskip60
    )
    yield (
        998,  # chain_id
        60,  # slip44
        "L99",  # shortcut
        "Lucky Network",  # name
        False,  # rskip60
    )
    yield (
        1000,  # chain_id
        60,  # slip44
        "GCD",  # shortcut
        "GTON",  # name
        False,  # rskip60
    )
    yield (
        1001,  # chain_id
        1,  # slip44
        "tKLAY",  # shortcut
        "Klaytn Testnet Baobab",  # name
        False,  # rskip60
    )
    yield (
        1007,  # chain_id
        1,  # slip44
        "tNEW",  # shortcut
        "Newton Testnet",  # name
        False,  # rskip60
    )
    yield (
        1008,  # chain_id
        60,  # slip44
        "EUN",  # shortcut
        "Eurus",  # name
        False,  # rskip60
    )
    yield (
        1010,  # chain_id
        1020,  # slip44
        "EVC",  # shortcut
        "Evrice Network",  # name
        False,  # rskip60
    )
    yield (
        1012,  # chain_id
        60,  # slip44
        "NEW",  # shortcut
        "Newton",  # name
        False,  # rskip60
    )
    yield (
        1022,  # chain_id
        60,  # slip44
        "SKU",  # shortcut
        "Sakura",  # name
        False,  # rskip60
    )
    yield (
        1024,  # chain_id
        60,  # slip44
        "CLV",  # shortcut
        "CLV Parachain",  # name
        False,  # rskip60
    )
    yield (
        1030,  # chain_id
        60,  # slip44
        "CFX",  # shortcut
        "Conflux eSpace",  # name
        False,  # rskip60
    )
    yield (
        1088,  # chain_id
        60,  # slip44
        "METIS",  # shortcut
        "Metis Andromeda",  # name
        False,  # rskip60
    )
    yield (
        1139,  # chain_id
        60,  # slip44
        "MATH",  # shortcut
        "MathChain",  # name
        False,  # rskip60
    )
    yield (
        1140,  # chain_id
        1,  # slip44
        "tMATH",  # shortcut
        "MathChain Testnet",  # name
        False,  # rskip60
    )
    yield (
        1197,  # chain_id
        60,  # slip44
        "IORA",  # shortcut
        "Iora Chain",  # name
        False,  # rskip60
    )
    yield (
        1202,  # chain_id
        60,  # slip44
        "WTT",  # shortcut
        "World Trade Technical Chain",  # name
        False,  # rskip60
    )
    yield (
        1213,  # chain_id
        60,  # slip44
        "POP",  # shortcut
        "Popcateum",  # name
        False,  # rskip60
    )
    yield (
        1214,  # chain_id
        60,  # slip44
        "ENTER",  # shortcut
        "EnterChain",  # name
        False,  # rskip60
    )
    yield (
        1246,  # chain_id
        60,  # slip44
        "OM",  # shortcut
        "OM Platform",  # name
        False,  # rskip60
    )
    yield (
        1280,  # chain_id
        60,  # slip44
        "HO",  # shortcut
        "HALO",  # name
        False,  # rskip60
    )
    yield (
        1284,  # chain_id
        60,  # slip44
        "GLMR",  # shortcut
        "Moonbeam",  # name
        False,  # rskip60
    )
    yield (
        1285,  # chain_id
        60,  # slip44
        "MOVR",  # shortcut
        "Moonriver",  # name
        False,  # rskip60
    )
    yield (
        1287,  # chain_id
        60,  # slip44
        "DEV",  # shortcut
        "Moonbase Alpha",  # name
        False,  # rskip60
    )
    yield (
        1288,  # chain_id
        60,  # slip44
        "ROC",  # shortcut
        "Moonrock",  # name
        False,  # rskip60
    )
    yield (
        1297,  # chain_id
        60,  # slip44
        "BOBA",  # shortcut
        "Boba Network Bobabase",  # name
        False,  # rskip60
    )
    yield (
        1319,  # chain_id
        60,  # slip44
        "AITD",  # shortcut
        "Aitd",  # name
        False,  # rskip60
    )
    yield (
        1506,  # chain_id
        60,  # slip44
        "KSX",  # shortcut
        "Sherpax",  # name
        False,  # rskip60
    )
    yield (
        1618,  # chain_id
        60,  # slip44
        "CATE",  # shortcut
        "Catecoin Chain",  # name
        False,  # rskip60
    )
    yield (
        1657,  # chain_id
        60,  # slip44
        "BTA",  # shortcut
        "Btachain",  # name
        False,  # rskip60
    )
    yield (
        1688,  # chain_id
        60,  # slip44
        "LUDAN",  # shortcut
        "LUDAN",  # name
        False,  # rskip60
    )
    yield (
        1818,  # chain_id
        1818,  # slip44
        "CUBE",  # shortcut
        "Cube Chain",  # name
        False,  # rskip60
    )
    yield (
        1856,  # chain_id
        60,  # slip44
        "TSF",  # shortcut
        "Teslafunds",  # name
        False,  # rskip60
    )
    yield (
        1898,  # chain_id
        60,  # slip44
        "BOY",  # shortcut
        "BON Network",  # name
        False,  # rskip60
    )
    yield (
        1987,  # chain_id
        1987,  # slip44
        "EGEM",  # shortcut
        "EtherGem",  # name
        False,  # rskip60
    )
    yield (
        2001,  # chain_id
        60,  # slip44
        "mADA",  # shortcut
        "Milkomeda C1",  # name
        False,  # rskip60
    )
    yield (
        2009,  # chain_id
        60,  # slip44
        "CWN",  # shortcut
        "CloudWalk",  # name
        False,  # rskip60
    )
    yield (
        2020,  # chain_id
        60,  # slip44
        "420",  # shortcut
        "420coin",  # name
        False,  # rskip60
    )
    yield (
        2021,  # chain_id
        60,  # slip44
        "EDG",  # shortcut
        "Edgeware",  # name
        False,  # rskip60
    )
    yield (
        2025,  # chain_id
        1008,  # slip44
        "RPG",  # shortcut
        "Rangers Protocol",  # name
        False,  # rskip60
    )
    yield (
        2100,  # chain_id
        60,  # slip44
        "ECO",  # shortcut
        "Ecoball",  # name
        False,  # rskip60
    )
    yield (
        2152,  # chain_id
        60,  # slip44
        "FRA",  # shortcut
        "Findora",  # name
        False,  # rskip60
    )
    yield (
        2213,  # chain_id
        60,  # slip44
        "EVA",  # shortcut
        "Evanesco",  # name
        False,  # rskip60
    )
    yield (
        2222,  # chain_id
        60,  # slip44
        "KAVA",  # shortcut
        "Kava EVM",  # name
        False,  # rskip60
    )
    yield (
        2223,  # chain_id
        60,  # slip44
        "VNDT",  # shortcut
        "VChain",  # name
        False,  # rskip60
    )
    yield (
        2559,  # chain_id
        60,  # slip44
        "KTO",  # shortcut
        "Kortho",  # name
        False,  # rskip60
    )
    yield (
        2569,  # chain_id
        60,  # slip44
        "TPC",  # shortcut
        "TechPay",  # name
        False,  # rskip60
    )
    yield (
        2612,  # chain_id
        60,  # slip44
        "EZC",  # shortcut
        "EZChain C-Chain",  # name
        False,  # rskip60
    )
    yield (
        3000,  # chain_id
        60,  # slip44
        "CPAY",  # shortcut
        "CENNZnet Rata",  # name
        False,  # rskip60
    )
    yield (
        3001,  # chain_id
        60,  # slip44
        "CPAY",  # shortcut
        "CENNZnet Nikau",  # name
        False,  # rskip60
    )
    yield (
        3400,  # chain_id
        60,  # slip44
        "PRB",  # shortcut
        "Paribu Net",  # name
        False,  # rskip60
    )
    yield (
        3501,  # chain_id
        60,  # slip44
        "jfin",  # shortcut
        "JFIN Chain",  # name
        False,  # rskip60
    )
    yield (
        3737,  # chain_id
        60,  # slip44
        "CSB",  # shortcut
        "Crossbell",  # name
        False,  # rskip60
    )
    yield (
        3966,  # chain_id
        60,  # slip44
        "DYNO",  # shortcut
        "DYNO",  # name
        False,  # rskip60
    )
    yield (
        3999,  # chain_id
        60,  # slip44
        "YCC",  # shortcut
        "YuanChain",  # name
        False,  # rskip60
    )
    yield (
        4181,  # chain_id
        60,  # slip44
        "Φ",  # shortcut
        "PHI Network",  # name
        False,  # rskip60
    )
    yield (
        4689,  # chain_id
        60,  # slip44
        "IOTX",  # shortcut
        "IoTeX Network",  # name
        False,  # rskip60
    )
    yield (
        4919,  # chain_id
        60,  # slip44
        "XVM",  # shortcut
        "Venidium",  # name
        False,  # rskip60
    )
    yield (
        5177,  # chain_id
        60,  # slip44
        "TLC",  # shortcut
        "TLChain Network",  # name
        False,  # rskip60
    )
    yield (
        5197,  # chain_id
        60,  # slip44
        "ES",  # shortcut
        "EraSwap",  # name
        False,  # rskip60
    )
    yield (
        5315,  # chain_id
        60,  # slip44
        "UZMI",  # shortcut
        "Uzmi Network",  # name
        False,  # rskip60
    )
    yield (
        5777,  # chain_id
        60,  # slip44
        "DGCC",  # shortcut
        "Digest Swarm Chain",  # name
        False,  # rskip60
    )
    yield (
        5869,  # chain_id
        60,  # slip44
        "RBD",  # shortcut
        "Wegochain Rubidium",  # name
        False,  # rskip60
    )
    yield (
        6626,  # chain_id
        60,  # slip44
        "PIX",  # shortcut
        "Pixie Chain",  # name
        False,  # rskip60
    )
    yield (
        6969,  # chain_id
        60,  # slip44
        "TOMB",  # shortcut
        "Tomb Chain",  # name
        False,  # rskip60
    )
    yield (
        8000,  # chain_id
        60,  # slip44
        "TELE",  # shortcut
        "Teleport",  # name
        False,  # rskip60
    )
    yield (
        8217,  # chain_id
        8217,  # slip44
        "KLAY",  # shortcut
        "Klaytn",  # name
        False,  # rskip60
    )
    yield (
        8723,  # chain_id
        479,  # slip44
        "OLO",  # shortcut
        "TOOL Global",  # name
        False,  # rskip60
    )
    yield (
        8898,  # chain_id
        60,  # slip44
        "MMT",  # shortcut
        "Mammoth",  # name
        False,  # rskip60
    )
    yield (
        8995,  # chain_id
        60,  # slip44
        "U+25B3",  # shortcut
        "bloxberg",  # name
        False,  # rskip60
    )
    yield (
        9001,  # chain_id
        60,  # slip44
        "EVMOS",  # shortcut
        "Evmos",  # name
        False,  # rskip60
    )
    yield (
        9012,  # chain_id
        60,  # slip44
        "BRB",  # shortcut
        "BerylBit",  # name
        False,  # rskip60
    )
    yield (
        9100,  # chain_id
        60,  # slip44
        "GNC",  # shortcut
        "Genesis Coin",  # name
        False,  # rskip60
    )
    yield (
        10101,  # chain_id
        60,  # slip44
        "GEN",  # shortcut
        "Blockchain Genesis",  # name
        False,  # rskip60
    )
    yield (
        10823,  # chain_id
        60,  # slip44
        "CCP",  # shortcut
        "CryptoCoinPay",  # name
        False,  # rskip60
    )
    yield (
        10946,  # chain_id
        60,  # slip44
        "QDC",  # shortcut
        "Quadrans Blockchain",  # name
        False,  # rskip60
    )
    yield (
        11111,  # chain_id
        60,  # slip44
        "WGM",  # shortcut
        "WAGMI",  # name
        False,  # rskip60
    )
    yield (
        12052,  # chain_id
        621,  # slip44
        "ZERO",  # shortcut
        "Singularity ZERO",  # name
        False,  # rskip60
    )
    yield (
        13381,  # chain_id
        60,  # slip44
        "PHX",  # shortcut
        "Phoenix",  # name
        False,  # rskip60
    )
    yield (
        16000,  # chain_id
        60,  # slip44
        "MTT",  # shortcut
        "MetaDot",  # name
        False,  # rskip60
    )
    yield (
        19845,  # chain_id
        60,  # slip44
        "BTCIX",  # shortcut
        "BTCIX Network",  # name
        False,  # rskip60
    )
    yield (
        21337,  # chain_id
        60,  # slip44
        "CPAY",  # shortcut
        "CENNZnet Azalea",  # name
        False,  # rskip60
    )
    yield (
        21816,  # chain_id
        60,  # slip44
        "OMC",  # shortcut
        "omChain",  # name
        False,  # rskip60
    )
    yield (
        22023,  # chain_id
        60,  # slip44
        "SFL",  # shortcut
        "Taycan",  # name
        False,  # rskip60
    )
    yield (
        24484,  # chain_id
        227,  # slip44
        "WEB",  # shortcut
        "Webchain",  # name
        False,  # rskip60
    )
    yield (
        24734,  # chain_id
        60,  # slip44
        "MINTME",  # shortcut
        "MintMe.com Coin",  # name
        False,  # rskip60
    )
    yield (
        26863,  # chain_id
        60,  # slip44
        "OAC",  # shortcut
        "OasisChain",  # name
        False,  # rskip60
    )
    yield (
        31102,  # chain_id
        31102,  # slip44
        "ESN",  # shortcut
        "Ethersocial Network",  # name
        False,  # rskip60
    )
    yield (
        32520,  # chain_id
        60,  # slip44
        "Brise",  # shortcut
        "Bitgert",  # name
        False,  # rskip60
    )
    yield (
        32659,  # chain_id
        60,  # slip44
        "FSN",  # shortcut
        "Fusion",  # name
        False,  # rskip60
    )
    yield (
        39797,  # chain_id
        39797,  # slip44
        "NRG",  # shortcut
        "Energi",  # name
        False,  # rskip60
    )
    yield (
        42069,  # chain_id
        60,  # slip44
        "peggle",  # shortcut
        "pegglecoin",  # name
        False,  # rskip60
    )
    yield (
        42220,  # chain_id
        60,  # slip44
        "CELO",  # shortcut
        "Celo",  # name
        False,  # rskip60
    )
    yield (
        42262,  # chain_id
        60,  # slip44
        "ROSE",  # shortcut
        "Emerald Paratime",  # name
        False,  # rskip60
    )
    yield (
        43113,  # chain_id
        1,  # slip44
        "tAVAX",  # shortcut
        "Avalanche Fuji Testnet",  # name
        False,  # rskip60
    )
    yield (
        43114,  # chain_id
        9005,  # slip44
        "AVAX",  # shortcut
        "Avalanche C-Chain",  # name
        False,  # rskip60
    )
    yield (
        44787,  # chain_id
        1,  # slip44
        "tCELO",  # shortcut
        "Celo Alfajores Testnet",  # name
        False,  # rskip60
    )
    yield (
        45000,  # chain_id
        60,  # slip44
        "TXL",  # shortcut
        "Autobahn Network",  # name
        False,  # rskip60
    )
    yield (
        47805,  # chain_id
        60,  # slip44
        "REI",  # shortcut
        "REI Network",  # name
        False,  # rskip60
    )
    yield (
        49797,  # chain_id
        1,  # slip44
        "tNRG",  # shortcut
        "Energi Testnet",  # name
        False,  # rskip60
    )
    yield (
        53935,  # chain_id
        60,  # slip44
        "JEWEL",  # shortcut
        "DFK Chain",  # name
        False,  # rskip60
    )
    yield (
        62320,  # chain_id
        1,  # slip44
        "tCELO",  # shortcut
        "Celo Baklava Testnet",  # name
        False,  # rskip60
    )
    yield (
        62621,  # chain_id
        60,  # slip44
        "MTV",  # shortcut
        "MultiVAC",  # name
        False,  # rskip60
    )
    yield (
        63000,  # chain_id
        60,  # slip44
        "ECS",  # shortcut
        "eCredits",  # name
        False,  # rskip60
    )
    yield (
        71402,  # chain_id
        60,  # slip44
        "pCKB",  # shortcut
        "Godwoken",  # name
        False,  # rskip60
    )
    yield (
        73799,  # chain_id
        1,  # slip44
        "tVT",  # shortcut
        "Energy Web Volta Testnet",  # name
        False,  # rskip60
    )
    yield (
        78110,  # chain_id
        60,  # slip44
        "FIN",  # shortcut
        "Firenze test network",  # name
        False,  # rskip60
    )
    yield (
        80001,  # chain_id
        1,  # slip44
        "tMATIC",  # shortcut
        "Mumbai",  # name
        False,  # rskip60
    )
    yield (
        88888,  # chain_id
        60,  # slip44
        "IVAR",  # shortcut
        "IVAR Chain",  # name
        False,  # rskip60
    )
    yield (
        99999,  # chain_id
        60,  # slip44
        "UBC",  # shortcut
        "UB Smart Chain",  # name
        False,  # rskip60
    )
    yield (
        100000,  # chain_id
        60,  # slip44
        "QKC",  # shortcut
        "QuarkChain",  # name
        False,  # rskip60
    )
    yield (
        100001,  # chain_id
        60,  # slip44
        "QKC",  # shortcut
        "QuarkChain",  # name
        False,  # rskip60
    )
    yield (
        100002,  # chain_id
        60,  # slip44
        "QKC",  # shortcut
        "QuarkChain",  # name
        False,  # rskip60
    )
    yield (
        100003,  # chain_id
        60,  # slip44
        "QKC",  # shortcut
        "QuarkChain",  # name
        False,  # rskip60
    )
    yield (
        100004,  # chain_id
        60,  # slip44
        "QKC",  # shortcut
        "QuarkChain",  # name
        False,  # rskip60
    )
    yield (
        100005,  # chain_id
        60,  # slip44
        "QKC",  # shortcut
        "QuarkChain",  # name
        False,  # rskip60
    )
    yield (
        100006,  # chain_id
        60,  # slip44
        "QKC",  # shortcut
        "QuarkChain",  # name
        False,  # rskip60
    )
    yield (
        100007,  # chain_id
        60,  # slip44
        "QKC",  # shortcut
        "QuarkChain",  # name
        False,  # rskip60
    )
    yield (
        100008,  # chain_id
        60,  # slip44
        "QKC",  # shortcut
        "QuarkChain",  # name
        False,  # rskip60
    )
    yield (
        103090,  # chain_id
        60,  # slip44
        "◈",  # shortcut
        "Crystaleum",  # name
        False,  # rskip60
    )
    yield (
        108801,  # chain_id
        60,  # slip44
        "BRO",  # shortcut
        "BROChain",  # name
        False,  # rskip60
    )
    yield (
        131419,  # chain_id
        60,  # slip44
        "ETND",  # shortcut
        "ETND Chain",  # name
        False,  # rskip60
    )
    yield (
        200625,  # chain_id
        200625,  # slip44
        "AKA",  # shortcut
        "Akroma",  # name
        False,  # rskip60
    )
    yield (
        201018,  # chain_id
        60,  # slip44
        "atp",  # shortcut
        "Alaya",  # name
        False,  # rskip60
    )
    yield (
        210425,  # chain_id
        60,  # slip44
        "lat",  # shortcut
        "PlatON",  # name
        False,  # rskip60
    )
    yield (
        246529,  # chain_id
        246529,  # slip44
        "ATS",  # shortcut
        "ARTIS sigma1",  # name
        False,  # rskip60
    )
    yield (
        246785,  # chain_id
        1,  # slip44
        "tATS",  # shortcut
        "ARTIS Testnet tau1",  # name
        False,  # rskip60
    )
    yield (
        281121,  # chain_id
        60,  # slip44
        "$OC",  # shortcut
        "Social Smart Chain",  # name
        False,  # rskip60
    )
    yield (
        333999,  # chain_id
        60,  # slip44
        "POLIS",  # shortcut
        "Polis",  # name
        False,  # rskip60
    )
    yield (
        474142,  # chain_id
        60,  # slip44
        "OPC",  # shortcut
        "OpenChain",  # name
        False,  # rskip60
    )
    yield (
        846000,  # chain_id
        60,  # slip44
        "APTA",  # shortcut
        "4GoodNetwork",  # name
        False,  # rskip60
    )
    yield (
        888888,  # chain_id
        60,  # slip44
        "VS",  # shortcut
        "Vision -",  # name
        False,  # rskip60
    )
    yield (
        955305,  # chain_id
        1011,  # slip44
        "ELV",  # shortcut
        "Eluvio Content Fabric",  # name
        False,  # rskip60
    )
    yield (
        1313114,  # chain_id
        1313114,  # slip44
        "ETHO",  # shortcut
        "Etho Protocol",  # name
        False,  # rskip60
    )
    yield (
        1313500,  # chain_id
        60,  # slip44
        "XERO",  # shortcut
        "Xerom",  # name
        False,  # rskip60
    )
    yield (
        7762959,  # chain_id
        184,  # slip44
        "MUSIC",  # shortcut
        "Musicoin",  # name
        False,  # rskip60
    )
    yield (
        11155111,  # chain_id
        1,  # slip44
        "tSEP",  # shortcut
        "Sepolia",  # name
        False,  # rskip60
    )
    yield (
        13371337,  # chain_id
        60,  # slip44
        "TPEP",  # shortcut
        "PepChain Churchill",  # name
        False,  # rskip60
    )
    yield (
        18289463,  # chain_id
        60,  # slip44
        "ILT",  # shortcut
        "IOLite",  # name
        False,  # rskip60
    )
    yield (
        20180430,  # chain_id
        60,  # slip44
        "SMT",  # shortcut
        "SmartMesh",  # name
        False,  # rskip60
    )
    yield (
        20181205,  # chain_id
        60,  # slip44
        "QKI",  # shortcut
        "quarkblockchain",  # name
        False,  # rskip60
    )
    yield (
        28945486,  # chain_id
        344,  # slip44
        "AUX",  # shortcut
        "Auxilium Network",  # name
        False,  # rskip60
    )
    yield (
        35855456,  # chain_id
        60,  # slip44
        "JOYS",  # shortcut
        "Joys Digital",  # name
        False,  # rskip60
    )
    yield (
        61717561,  # chain_id
        61717561,  # slip44
        "AQUA",  # shortcut
        "Aquachain",  # name
        False,  # rskip60
    )
    yield (
        99415706,  # chain_id
        1,  # slip44
        "TOYS",  # shortcut
        "Joys Digital TestNet",  # name
        False,  # rskip60
    )
    yield (
        245022934,  # chain_id
        60,  # slip44
        "NEON",  # shortcut
        "Neon EVM",  # name
        False,  # rskip60
    )
    yield (
        311752642,  # chain_id
        60,  # slip44
        "OLT",  # shortcut
        "OneLedger",  # name
        False,  # rskip60
    )
    yield (
        1122334455,  # chain_id
        60,  # slip44
        "IPOS",  # shortcut
        "IPOS Network",  # name
        False,  # rskip60
    )
    yield (
        1666600000,  # chain_id
        60,  # slip44
        "ONE",  # shortcut
        "Harmony",  # name
        False,  # rskip60
    )
    yield (
        1666600001,  # chain_id
        60,  # slip44
        "ONE",  # shortcut
        "Harmony",  # name
        False,  # rskip60
    )
    yield (
        1666600002,  # chain_id
        60,  # slip44
        "ONE",  # shortcut
        "Harmony",  # name
        False,  # rskip60
    )
    yield (
        1666600003,  # chain_id
        60,  # slip44
        "ONE",  # shortcut
        "Harmony",  # name
        False,  # rskip60
    )
    yield (
        2021121117,  # chain_id
        60,  # slip44
        "HOP",  # shortcut
        "DataHopper",  # name
        False,  # rskip60
    )
    yield (
        3125659152,  # chain_id
        164,  # slip44
        "PIRL",  # shortcut
        "Pirl",  # name
        False,  # rskip60
    )
    yield (
        11297108109,  # chain_id
        60,  # slip44
        "PALM",  # shortcut
        "Palm",  # name
        False,  # rskip60
    )
    yield (
        197710212030,  # chain_id
        60,  # slip44
        "NTT",  # shortcut
        "Ntity",  # name
        False,  # rskip60
    )
    yield (
        6022140761023,  # chain_id
        60,  # slip44
        "MOLE",  # shortcut
        "Molereum Network",  # name
        False,  # rskip60
    )
