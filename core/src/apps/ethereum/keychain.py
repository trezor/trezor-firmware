from typing import TYPE_CHECKING

from apps.common import paths
from apps.common.keychain import get_keychain

from . import CURVE, networks, definitions

if TYPE_CHECKING:
    from typing import Awaitable, Callable, Iterable, TypeVar

    from apps.common.keychain import Keychain

    from trezor.wire import Context

    from trezor.messages import (
        EthereumGetAddress,
        EthereumGetPublicKey,
        EthereumSignMessage,
        EthereumSignTx,
        EthereumSignTxEIP1559,
        EthereumSignTypedData,
    )

    from apps.common.keychain import MsgIn as MsgInGeneric, MsgOut, Handler, HandlerWithKeychain

    # messages for "with_keychain_from_path" decorator
    MsgInKeychainPath = TypeVar("MsgInKeychainPath", bound=EthereumGetPublicKey)
    # messages for "with_keychain_from_path_and_defs" decorator
    MsgInKeychainPathDefs = TypeVar("MsgInKeychainPathDefs", bound=EthereumGetAddress | EthereumSignMessage | EthereumSignTypedData)
    # messages for "with_keychain_from_chain_id_and_defs" decorator
    MsgInKeychainChainIdDefs = TypeVar("MsgInKeychainChainIdDefs", bound=EthereumSignTx | EthereumSignTxEIP1559)

    # TODO: check the types of messages
    HandlerWithKeychainAndDefinitions = Callable[[Context, MsgInGeneric, Keychain, definitions.EthereumDefinitions], Awaitable[MsgOut]]


# We believe Ethereum should use 44'/60'/a' for everything, because it is
# account-based, rather than UTXO-based. Unfortunately, lot of Ethereum
# tools (MEW, Metamask) do not use such scheme and set a = 0 and then
# iterate the address index i. For compatibility, we allow this scheme as well.
# Also to support "Ledger Live" legacy paths we allow 44'/60'/0'/a paths.

PATTERNS_ADDRESS = (
    paths.PATTERN_BIP44,
    paths.PATTERN_SEP5,
    paths.PATTERN_SEP5_LEDGER_LIVE_LEGACY,
)


def _schemas_from_address_n(
    patterns: Iterable[str], address_n: paths.Bip32Path, network_info: networks.NetworkInfo | None
) -> Iterable[paths.PathSchema]:
    if len(address_n) < 2:
        return ()

    slip44_hardened = address_n[1]

    def _get_hardened_slip44_networks():
        if network_info is not None:
            yield network_info.slip44 | paths.HARDENED
        yield from networks.all_slip44_ids_hardened()

    # check with network from definitions and if that is None then with built-in ones
    if slip44_hardened not in _get_hardened_slip44_networks():
        return ()

    if not slip44_hardened & paths.HARDENED:
        return ()

    slip44_id = slip44_hardened - paths.HARDENED
    schemas = [paths.PathSchema.parse(pattern, slip44_id) for pattern in patterns]
    return [s.copy() for s in schemas]


def with_keychain_from_path(
    *patterns: str,
) -> Callable[[HandlerWithKeychain[MsgInKeychainPath, MsgOut]], Handler[MsgInKeychainPath, MsgOut]]:
    def decorator(func: HandlerWithKeychain[MsgInKeychainPath, MsgOut]) -> Handler[MsgInKeychainPath, MsgOut]:
        async def wrapper(ctx: Context, msg: MsgInKeychainPath) -> MsgOut:
            defs = definitions.get_definitions_from_msg(msg)
            schemas = _schemas_from_address_n(patterns, msg.address_n, defs.network)
            keychain = await get_keychain(ctx, CURVE, schemas)
            with keychain:
                return await func(ctx, msg, keychain)

        return wrapper

    return decorator


def with_keychain_from_path_and_defs(
    *patterns: str,
) -> Callable[[HandlerWithKeychainAndDefinitions[MsgInKeychainPathDefs, MsgOut]], Handler[MsgInKeychainPathDefs, MsgOut]]:
    def decorator(func: HandlerWithKeychainAndDefinitions[MsgInKeychainPathDefs, MsgOut]) -> Handler[MsgInKeychainPathDefs, MsgOut]:
        async def wrapper(ctx: Context, msg: MsgInKeychainPathDefs) -> MsgOut:
            defs = definitions.get_definitions_from_msg(msg)
            schemas = _schemas_from_address_n(patterns, msg.address_n, defs.network)
            keychain = await get_keychain(ctx, CURVE, schemas)
            with keychain:
                return await func(ctx, msg, keychain, defs)

        return wrapper

    return decorator


def _schemas_from_chain_id(network_info: networks.NetworkInfo | None) -> Iterable[paths.PathSchema]:
    slip44_id: tuple[int, ...]
    if network_info is None:
        # allow Ethereum or testnet paths for unknown networks
        slip44_id = (60, 1)
    elif network_info.slip44 not in (60, 1):
        # allow cross-signing with Ethereum unless it's testnet
        slip44_id = (network_info.slip44, 60)
    else:
        slip44_id = (network_info.slip44,)

    schemas = [
        paths.PathSchema.parse(pattern, slip44_id) for pattern in PATTERNS_ADDRESS
    ]
    return [s.copy() for s in schemas]


def with_keychain_from_chain_id_and_defs(
    func: HandlerWithKeychainAndDefinitions[MsgInKeychainChainIdDefs, MsgOut]
) -> Handler[MsgInKeychainChainIdDefs, MsgOut]:
    # this is only for SignTx, and only PATTERN_ADDRESS is allowed
    async def wrapper(ctx: Context, msg: MsgInKeychainChainIdDefs) -> MsgOut:
        defs = definitions.get_definitions_from_msg(msg)
        schemas = _schemas_from_chain_id(defs.network)
        keychain = await get_keychain(ctx, CURVE, schemas)
        with keychain:
            return await func(ctx, msg, keychain, defs)

    return wrapper
