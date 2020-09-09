from trezor import wire

from apps.common import HARDENED, coininfo
from apps.common.keychain import get_keychain

from .common import BITCOIN_NAMES

if False:
    from protobuf import MessageType
    from typing import Callable, Optional, Tuple, TypeVar
    from typing_extensions import Protocol

    from apps.common.keychain import Keychain, MsgOut, Handler

    from .authorization import CoinJoinAuthorization

    class MsgWithCoinName(MessageType, Protocol):
        coin_name = ...  # type: Optional[str]

    MsgIn = TypeVar("MsgIn", bound=MsgWithCoinName)
    HandlerWithCoinInfo = Callable[
        [wire.Context, MsgIn, Keychain, coininfo.CoinInfo], MsgOut
    ]


def get_namespaces_for_coin(coin: coininfo.CoinInfo):
    namespaces = []
    slip44_id = coin.slip44 | HARDENED

    # BIP-44 - legacy: m/44'/slip44' (/account'/change/addr)
    namespaces.append([44 | HARDENED, slip44_id])
    # BIP-45 - multisig cosigners: m/45' (/cosigner/change/addr)
    namespaces.append([45 | HARDENED])
    # "purpose48" - multisig as done by Electrum
    # m/48'/slip44' (/account'/script_type'/change/addr)
    namespaces.append([48 | HARDENED, slip44_id])

    if coin.segwit:
        # BIP-49 - p2sh segwit: m/49'/slip44' (/account'/change/addr)
        namespaces.append([49 | HARDENED, slip44_id])
        # BIP-84 - native segwit: m/84'/slip44' (/account'/change/addr)
        namespaces.append([84 | HARDENED, slip44_id])

    if coin.coin_name in BITCOIN_NAMES:
        # compatibility namespace for Casa
        namespaces.append([49, coin.slip44])

        # compatibility namespace for Greenaddress:
        # m/branch/address_pointer, for branch in (1, 4)
        namespaces.append([1])
        namespaces.append([4])
        # m/3'/subaccount'/branch/address_pointer
        namespaces.append([3 | HARDENED])
        # sign msg:
        # m/0x4741b11e
        # m/0x4741b11e/6/pointer
        namespaces.append([0x4741B11E])

    # some wallets such as Electron-Cash (BCH) store coins on Bitcoin paths
    # we can allow spending these coins from Bitcoin paths if the coin has
    # implemented strong replay protection via SIGHASH_FORKID
    if coin.fork_id is not None:
        namespaces.append([44 | HARDENED, 0 | HARDENED])
        namespaces.append([48 | HARDENED, 0 | HARDENED])
        if coin.segwit:
            namespaces.append([49 | HARDENED, 0 | HARDENED])
            namespaces.append([84 | HARDENED, 0 | HARDENED])

    return namespaces


def get_coin_by_name(coin_name: Optional[str]) -> coininfo.CoinInfo:
    if coin_name is None:
        coin_name = "Bitcoin"

    try:
        return coininfo.by_name(coin_name)
    except ValueError:
        raise wire.DataError("Unsupported coin type")


async def get_keychain_for_coin(
    ctx: wire.Context, coin_name: Optional[str]
) -> Tuple[Keychain, coininfo.CoinInfo]:
    coin = get_coin_by_name(coin_name)
    namespaces = get_namespaces_for_coin(coin)
    slip21_namespaces = [[b"SLIP-0019"]]
    keychain = await get_keychain(ctx, coin.curve_name, namespaces, slip21_namespaces)
    return keychain, coin


def with_keychain(func: HandlerWithCoinInfo[MsgIn, MsgOut]) -> Handler[MsgIn, MsgOut]:
    async def wrapper(
        ctx: wire.Context,
        msg: MsgIn,
        authorization: Optional[CoinJoinAuthorization] = None,
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
