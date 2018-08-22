# generated from coininfo.py.mako
# do not edit manually!
from trezor.crypto.base58 import groestl512d_32, sha256d_32


class CoinInfo:
    def __init__(
        self,
        coin_name: str,
        coin_shortcut: str,
        address_type: int,
        address_type_p2sh: int,
        maxfee_kb: int,
        signed_message_header: str,
        xpub_magic: int,
        bech32_prefix: str,
        cashaddr_prefix: str,
        slip44: int,
        segwit: bool,
        fork_id: int,
        force_bip143: bool,
        version_group_id: int,
        bip115: bool,
        curve_name: str,
    ):
        self.coin_name = coin_name
        self.coin_shortcut = coin_shortcut
        self.address_type = address_type
        self.address_type_p2sh = address_type_p2sh
        self.maxfee_kb = maxfee_kb
        self.signed_message_header = signed_message_header
        self.xpub_magic = xpub_magic
        self.bech32_prefix = bech32_prefix
        self.cashaddr_prefix = cashaddr_prefix
        self.slip44 = slip44
        self.segwit = segwit
        self.fork_id = fork_id
        self.force_bip143 = force_bip143
        self.version_group_id = version_group_id
        self.bip115 = bip115
        self.curve_name = curve_name
        if curve_name == "secp256k1-groestl":
            self.b58_hash = groestl512d_32
            self.sign_hash_double = False
        else:
            self.b58_hash = sha256d_32
            self.sign_hash_double = True


# fmt: off
<%
def hexfmt(x):
    if x is None:
        return None
    else:
        return "0x{:08x}".format(x)

ATTRIBUTES = (
    ("coin_name", black_repr),
    ("coin_shortcut", black_repr),
    ("address_type", int),
    ("address_type_p2sh", int),
    ("maxfee_kb", int),
    ("signed_message_header", black_repr),
    ("xpub_magic", hexfmt),
    ("bech32_prefix", black_repr),
    ("cashaddr_prefix", black_repr),
    ("slip44", int),
    ("segwit", bool),
    ("fork_id", black_repr),
    ("force_bip143", bool),
    ("version_group_id", hexfmt),
    ("bip115", bool),
    ("curve_name", lambda r: repr(r.replace("_", "-"))),
)
%>\
COINS = [
% for coin in supported_on("trezor2", bitcoin):
    CoinInfo(
        % for attr, func in ATTRIBUTES:
        ${attr}=${func(coin[attr])},
        % endfor
    ),
% endfor
]
