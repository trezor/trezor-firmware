# generated from coininfo.py.mako
# (by running `make templates` in `core`)
# do not edit manually!
from typing import Any, Optional

from .messages import CoinInfo

# flake8: noqa

<%
def hexfmt(x):
    if x is None:
        return None
    else:
        return "0x{:08x}".format(x)

def optional_dict(x):
    if x is None:
        return None
    return dict(x)

ATTRIBUTES = (
    ("coin_name", lambda _: "name", "str"),
    ("coin_shortcut", black_repr, "str"),
    ("decimals", int, "int"),
    ("address_type", int, "int"),
    ("address_type_p2sh", int, "int"),
    ("maxfee_kb", int, "int"),
    ("signed_message_header", black_repr, "str"),
    ("xpub_magic", hexfmt, "int"),
    ("xpub_magic_segwit_p2sh", hexfmt, "Optional[int]"),
    ("xpub_magic_segwit_native", hexfmt, "Optional[int]"),
    ("xpub_magic_multisig_segwit_p2sh", hexfmt, "Optional[int]"),
    ("xpub_magic_multisig_segwit_native", hexfmt, "Optional[int]"),
    ("bech32_prefix", black_repr, "Optional[str]"),
    ("cashaddr_prefix", black_repr, "Optional[str]"),
    ("slip44", int, "int"),
    ("segwit", bool, "bool"),
    ("taproot", bool, "bool"),
    ("fork_id", black_repr, "Optional[int]"),
    ("force_bip143", bool, "bool"),
    ("decred", bool, "bool"),
    ("negative_fee", bool, "bool"),
    ("curve_name", lambda r: repr(r.replace("_", "-")), "str"),
    ("extra_data", bool, "bool"),
    ("timestamp", bool, "bool"),
    ("overwintered", bool, "bool"),
    ## ("confidential_assets", optional_dict, "Optional[dict[str, Any]]"),
)

btc_names = ["Bitcoin", "Testnet", "Regtest"]

coins_btc = [c for c in supported_on("trezor2", bitcoin) if c.name in btc_names]
coins_alt = [c for c in supported_on("trezor2", bitcoin) if c.name not in btc_names]

for c in coins_btc + coins_alt:
    c.overwintered = bool(c.consensus_branch_id)

%>\

# fmt: off

def by_name(name: str) -> CoinInfo:
% for coin in coins_btc:
    if name == ${black_repr(coin["coin_name"])}:
        return CoinInfo(
            % for attr, func, _ in ATTRIBUTES:
            ${attr}=${func(coin[attr])},
            % endfor
        )
% endfor
% for coin in coins_alt:
    if name == ${black_repr(coin["coin_name"])}:
        return CoinInfo(
            % for attr, func, _ in ATTRIBUTES:
            ${attr}=${func(coin[attr])},
            % endfor
        )
% endfor
    raise ValueError  # Unknown coin name
