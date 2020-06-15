from trezor import wire

from apps.common import HARDENED, coininfo
from apps.common.seed import get_keychain

if False:
    from protobuf import MessageType
    from typing import Callable, Optional, Tuple, TypeVar
    from typing_extensions import Protocol

    from apps.common.seed import Keychain, MsgOut, Handler

    class MsgWithCoinName(MessageType, Protocol):
        coin_name = ...  # type: Optional[str]

    MsgIn = TypeVar("MsgIn", bound=MsgWithCoinName)
    HandlerWithCoinInfo = Callable[
        [wire.Context, MsgIn, Keychain, coininfo.CoinInfo], MsgOut
    ]


def get_namespaces_for_coin(coin: coininfo.CoinInfo):
    namespaces = []
    curve = coin.curve_name
    slip44_id = coin.slip44 | HARDENED

    # BIP-44 - legacy: m/44'/slip44' (/account'/change/addr)
    namespaces.append((curve, [44 | HARDENED, slip44_id]))
    # BIP-45 - multisig cosigners: m/45' (/cosigner/change/addr)
    namespaces.append((curve, [45 | HARDENED]))
    # "purpose48" - multisig as done by Electrum
    # m/48'/slip44' (/account'/script_type'/change/addr)
    namespaces.append((curve, [48 | HARDENED, slip44_id]))

    namespaces.append(("slip21", [b"SLIP-0019"]))

    if coin.segwit:
        # BIP-49 - p2sh segwit: m/49'/slip44' (/account'/change/addr)
        namespaces.append((curve, [49 | HARDENED, slip44_id]))
        # BIP-84 - native segwit: m/84'/slip44' (/account'/change/addr)
        namespaces.append((curve, [84 | HARDENED, slip44_id]))

    return namespaces


async def get_keychain_for_coin(
    ctx: wire.Context, coin_name: Optional[str]
) -> Tuple[Keychain, coininfo.CoinInfo]:
    if coin_name is None:
        coin_name = "Bitcoin"

    try:
        coin = coininfo.by_name(coin_name)
    except ValueError:
        raise wire.DataError("Unsupported coin type")

    namespaces = get_namespaces_for_coin(coin)
    keychain = await get_keychain(ctx, namespaces)
    return keychain, coin


def with_keychain(func: HandlerWithCoinInfo[MsgIn, MsgOut]) -> Handler[MsgIn, MsgOut]:
    async def wrapper(ctx: wire.Context, msg: MsgIn) -> MsgOut:
        keychain, coin = await get_keychain_for_coin(ctx, msg.coin_name)
        with keychain:
            return await func(ctx, msg, keychain, coin)

    return wrapper
