# generated from coininfo.py.mako
# (by running `make templates` in `core`)
# do not edit manually!
from typing import NamedTuple, TYPE_CHECKING

import trezorproto

from trezor import utils, wire
from trezor.crypto.base58 import blake256d_32, groestl512d_32, keccak_32, sha256d_32
from trezor.crypto.curve import ed25519
from trezor.crypto.hashlib import sha256
from trezor.crypto.scripts import blake256_ripemd160, sha256_ripemd160
from trezor.enums import CoinInfoAckType
from trezor.messages import CoinInfo, CoinInfoAck, CoinInfoRequest
from ubinascii import unhexlify

if TYPE_CHECKING:
    from typing import Awaitable, Callable, TypeVar
    from trezor import wire

    # type for CoinInfo class
    T = TypeVar('T', bound='CoinInfo')

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
    ("xpub_magic_segwit_p2sh", hexfmt, "int | None"),
    ("xpub_magic_segwit_native", hexfmt, "int | None"),
    ("xpub_magic_multisig_segwit_p2sh", hexfmt, "int | None"),
    ("xpub_magic_multisig_segwit_native", hexfmt, "int | None"),
    ("bech32_prefix", black_repr, "str | None"),
    ("cashaddr_prefix", black_repr, "str | None"),
    ("slip44", int, "int"),
    ("segwit", bool, "bool"),
    ("taproot", bool, "bool"),
    ("fork_id", black_repr, "int | None"),
    ("force_bip143", bool, "bool"),
    ("decred", bool, "bool"),
    ("negative_fee", bool, "bool"),
    ("curve_name", lambda r: repr(r.replace("_", "-")), "str"),
    ("extra_data", bool, "bool"),
    ("timestamp", bool, "bool"),
    ("overwintered", bool, "bool"),
)

btc_names = ["Bitcoin", "Testnet", "Regtest"]

coins_btc = [c for c in supported_on("trezor2", bitcoin) if c.name in btc_names]
coins_alt = [c for c in supported_on("trezor2", bitcoin) if c.name not in btc_names]

for c in coins_btc + coins_alt:
    c.overwintered = bool(c.consensus_branch_id)

%>\


class CoinHashInfo():
    def __init__(
        self,
        b58_hash: Callable[[bytes], bytes],
        sign_hash_double: bool,
        script_hash: type[utils.HashContextInitable],
    ) -> None:
        self.b58_hash = b58_hash
        self.sign_hash_double = sign_hash_double
        self.script_hash = script_hash


def get_CoinHashInfo(coin: CoinInfo) -> CoinHashInfo:
    if coin.curve_name == "secp256k1-groestl":
        return CoinHashInfo(groestl512d_32, False, sha256_ripemd160)
    elif coin.curve_name == "secp256k1-decred":
        return CoinHashInfo(blake256d_32, False, blake256_ripemd160)
    elif coin.curve_name == "secp256k1-smart":
        return CoinHashInfo(keccak_32, False, sha256_ripemd160)
    else:
        return CoinHashInfo(sha256d_32, True, sha256_ripemd160)


# TODO: somehow include this into `by_name` function
async def get_coin_from_host(ctx: wire.Context, name: str) -> CoinInfo:
    res = await ctx.call(CoinInfoRequest(), CoinInfoAck)

    # TODO: remove
    # "get" public key
    verify_key = unhexlify("db995fe25169d141cab9bbba92baa01f9f2e1ece7df4cb2ac05190f37fcc1f9d")
    # get sha256 of data
    data_hash = sha256(res.encoded_coin).digest()

    # verify signature
    if not ed25519.verify(verify_key, res.signature, data_hash):
        raise wire.ProcessError("Invalid signature")

    # load data
    if res.code == CoinInfoAckType.Bitcoin:
        ci = trezorproto.decode(res.encoded_coin, CoinInfo, True)
    else:
        raise ValueError  # Unknown coin type

    return ci

# fmt: off

# TODO: rename
def by_name(name: str) -> CoinInfo:
% for coin in coins_btc:
    if name == ${black_repr(coin["coin_name"])}:
        return CoinInfo(
            % for attr, func, _ in ATTRIBUTES:
            ${attr}=${func(coin[attr])},
            % endfor
        )
% endfor
    if not utils.BITCOIN_ONLY:
% for coin in coins_alt:
        if name == ${black_repr(coin["coin_name"])}:
            return CoinInfo(
                % for attr, func, _ in ATTRIBUTES:
                ${attr}=${func(coin[attr])},
                % endfor
            )
% endfor
    raise ValueError  # Unknown coin name
##
##     return await ctx.call(CoinInfoRequest(), CoinInfo)
