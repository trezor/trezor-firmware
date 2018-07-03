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


# generated using tools/codegen/gen_eth_networks.py
# do not edit manually!
# fmt: off
NETWORKS = [
    NetworkInfo(
        chain_id=1,
        slip44=60,
        shortcut='ETH',
        name='Ethereum',
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=2,
        slip44=40,
        shortcut='EXP',
        name='Expanse',
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=3,
        slip44=1,
        shortcut='tETH',
        name='Ethereum Testnet Ropsten',
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=4,
        slip44=1,
        shortcut='tETH',
        name='Ethereum Testnet Rinkeby',
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=8,
        slip44=108,
        shortcut='UBQ',
        name='UBIQ',
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=20,
        slip44=2018,
        shortcut='EOSC',
        name='EOS Classic',
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=28,
        slip44=1128,
        shortcut='ETSC',
        name='Ethereum Social',
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=30,
        slip44=137,
        shortcut='RSK',
        name='RSK',
        rskip60=True,
    ),
    NetworkInfo(
        chain_id=31,
        slip44=37310,
        shortcut='tRSK',
        name='RSK Testnet',
        rskip60=True,
    ),
    NetworkInfo(
        chain_id=42,
        slip44=1,
        shortcut='tETH',
        name='Ethereum Testnet Kovan',
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=61,
        slip44=61,
        shortcut='ETC',
        name='Ethereum Classic',
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=62,
        slip44=1,
        shortcut='tETC',
        name='Ethereum Classic Testnet',
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=64,
        slip44=163,
        shortcut='ELLA',
        name='Ellaism',
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=820,
        slip44=820,
        shortcut='CLO',
        name='Callisto',
        rskip60=False,
    ),
    NetworkInfo(
        chain_id=1987,
        slip44=1987,
        shortcut='EGEM',
        name='EtherGem',
        rskip60=False,
    ),
]
