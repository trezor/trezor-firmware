import gc

from trezor import wire
from trezor.messages import InputScriptType as I

from apps.common import coininfo
from apps.common.keychain import get_keychain
from apps.common.paths import PATTERN_BIP44, PathSchema

from .common import BITCOIN_NAMES

if False:
    from typing import Awaitable, Callable, Iterable, TypeVar
    from typing_extensions import Protocol

    from trezor.messages.TxInputType import EnumTypeInputScriptType

    from apps.common.keychain import Keychain, MsgOut, Handler
    from apps.common.paths import Bip32Path

    from .authorization import CoinJoinAuthorization

    class MsgWithCoinName(Protocol):
        coin_name: str

    class MsgWithAddressScriptType(Protocol):
        # XXX should be Bip32Path but that fails
        address_n: list[int] = ...
        script_type: EnumTypeInputScriptType = ...

    MsgIn = TypeVar("MsgIn", bound=MsgWithCoinName)
    HandlerWithCoinInfo = Callable[..., Awaitable[MsgOut]]


# BIP-45 for multisig: https://github.com/bitcoin/bips/blob/master/bip-0045.mediawiki
PATTERN_BIP45 = "m/45'/[0-100]/change/address_index"

# Electrum Purpose48. See docs/misc/purpose48.md
# Electrum does not seem to use the raw script type, it is included here for completeness.
PATTERN_PURPOSE48_RAW = "m/48'/coin_type'/account'/0'/change/address_index"
PATTERN_PURPOSE48_P2SHSEGWIT = "m/48'/coin_type'/account'/1'/change/address_index"
PATTERN_PURPOSE48_SEGWIT = "m/48'/coin_type'/account'/2'/change/address_index"

# BIP-49 for segwit-in-P2SH: https://github.com/bitcoin/bips/blob/master/bip-0049.mediawiki
PATTERN_BIP49 = "m/49'/coin_type'/account'/change/address_index"
# BIP-84 for segwit: https://github.com/bitcoin/bips/blob/master/bip-0084.mediawiki
PATTERN_BIP84 = "m/84'/coin_type'/account'/change/address_index"

# compatibility patterns, will be removed in the future
PATTERN_GREENADDRESS_A = "m/[1,4]/address_index"
PATTERN_GREENADDRESS_B = "m/3'/[1-100]'/[1,4]/address_index"
PATTERN_GREENADDRESS_SIGN_A = "m/1195487518"
PATTERN_GREENADDRESS_SIGN_B = "m/1195487518/6/address_index"

PATTERN_CASA = "m/49/coin_type/account/change/address_index"

PATTERN_UNCHAINED_HARDENED = (
    "m/45'/coin_type'/account'/[0-1000000]/change/address_index"
)
PATTERN_UNCHAINED_UNHARDENED = (
    "m/45'/coin_type/account/[0-1000000]/change/address_index"
)
PATTERN_UNCHAINED_DEPRECATED = "m/45'/coin_type'/account'/[0-1000000]/address_index"


def validate_path_against_script_type(
    coin: coininfo.CoinInfo,
    msg: MsgWithAddressScriptType | None = None,
    address_n: Bip32Path | None = None,
    script_type: EnumTypeInputScriptType | None = None,
    multisig: bool = False,
) -> bool:
    patterns = []

    if msg is not None:
        assert address_n is None and script_type is None
        address_n = msg.address_n
        script_type = msg.script_type or I.SPENDADDRESS
        multisig = bool(getattr(msg, "multisig", False))

    else:
        assert address_n is not None and script_type is not None

    if script_type == I.SPENDADDRESS and not multisig:
        patterns.append(PATTERN_BIP44)
        if coin.coin_name in BITCOIN_NAMES:
            patterns.append(PATTERN_GREENADDRESS_A)
            patterns.append(PATTERN_GREENADDRESS_B)

    elif script_type in (I.SPENDADDRESS, I.SPENDMULTISIG) and multisig:
        patterns.append(PATTERN_BIP45)
        patterns.append(PATTERN_PURPOSE48_RAW)
        if coin.coin_name in BITCOIN_NAMES:
            patterns.append(PATTERN_GREENADDRESS_A)
            patterns.append(PATTERN_GREENADDRESS_B)
            patterns.append(PATTERN_UNCHAINED_HARDENED)
            patterns.append(PATTERN_UNCHAINED_UNHARDENED)
            patterns.append(PATTERN_UNCHAINED_DEPRECATED)

    elif coin.segwit and script_type == I.SPENDP2SHWITNESS:
        patterns.append(PATTERN_BIP49)
        if multisig:
            patterns.append(PATTERN_PURPOSE48_P2SHSEGWIT)
        if coin.coin_name in BITCOIN_NAMES:
            patterns.append(PATTERN_GREENADDRESS_A)
            patterns.append(PATTERN_GREENADDRESS_B)
            patterns.append(PATTERN_CASA)

    elif coin.segwit and script_type == I.SPENDWITNESS:
        patterns.append(PATTERN_BIP84)
        if multisig:
            patterns.append(PATTERN_PURPOSE48_SEGWIT)
        if coin.coin_name in BITCOIN_NAMES:
            patterns.append(PATTERN_GREENADDRESS_A)
            patterns.append(PATTERN_GREENADDRESS_B)

    return any(
        PathSchema.parse(pattern, coin.slip44).match(address_n) for pattern in patterns
    )


def get_schemas_for_coin(coin: coininfo.CoinInfo) -> Iterable[PathSchema]:
    # basic patterns
    patterns = [
        PATTERN_BIP44,
        PATTERN_BIP45,
        PATTERN_PURPOSE48_RAW,
    ]

    # compatibility patterns
    if coin.coin_name in BITCOIN_NAMES:
        patterns.extend(
            (
                PATTERN_GREENADDRESS_A,
                PATTERN_GREENADDRESS_B,
                PATTERN_GREENADDRESS_SIGN_A,
                PATTERN_GREENADDRESS_SIGN_B,
                PATTERN_CASA,
                PATTERN_UNCHAINED_HARDENED,
                PATTERN_UNCHAINED_UNHARDENED,
                PATTERN_UNCHAINED_DEPRECATED,
            )
        )

    # segwit patterns
    if coin.segwit:
        patterns.extend(
            (
                PATTERN_BIP49,
                PATTERN_BIP84,
                PATTERN_PURPOSE48_P2SHSEGWIT,
                PATTERN_PURPOSE48_SEGWIT,
            )
        )

    schemas = [PathSchema.parse(pattern, coin.slip44) for pattern in patterns]

    # some wallets such as Electron-Cash (BCH) store coins on Bitcoin paths
    # we can allow spending these coins from Bitcoin paths if the coin has
    # implemented strong replay protection via SIGHASH_FORKID
    if coin.fork_id is not None:
        schemas.extend(PathSchema.parse(pattern, 0) for pattern in patterns)

    gc.collect()
    return [schema.copy() for schema in schemas]


def get_coin_by_name(coin_name: str | None) -> coininfo.CoinInfo:
    if coin_name is None:
        coin_name = "Bitcoin"

    try:
        return coininfo.by_name(coin_name)
    except ValueError:
        raise wire.DataError("Unsupported coin type")


async def get_keychain_for_coin(
    ctx: wire.Context, coin_name: str | None
) -> tuple[Keychain, coininfo.CoinInfo]:
    coin = get_coin_by_name(coin_name)
    schemas = get_schemas_for_coin(coin)
    slip21_namespaces = [[b"SLIP-0019"]]
    keychain = await get_keychain(ctx, coin.curve_name, schemas, slip21_namespaces)
    return keychain, coin


def with_keychain(func: HandlerWithCoinInfo[MsgOut]) -> Handler[MsgIn, MsgOut]:
    async def wrapper(
        ctx: wire.Context,
        msg: MsgIn,
        authorization: CoinJoinAuthorization | None = None,
    ) -> MsgOut:
        if authorization:
            keychain = authorization.keychain
            coin = get_coin_by_name(msg.coin_name)
            return await func(ctx, msg, keychain, coin, authorization)
        else:
            keychain, coin = await get_keychain_for_coin(ctx, msg.coin_name)
            with keychain:
                return await func(ctx, msg, keychain, coin)

    return wrapper
