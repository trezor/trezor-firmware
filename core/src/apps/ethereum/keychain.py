from typing import TYPE_CHECKING

from trezor.messages import EthereumNetworkInfo

from apps.common import paths
from apps.common.keychain import get_keychain

from . import CURVE, definitions, networks

if TYPE_CHECKING:
    from typing import Awaitable, Callable, Iterable, TypeVar

    from apps.common.keychain import Keychain

    from trezor.wire import Context

    from trezor.messages import (
        EthereumGetAddress,
        EthereumSignMessage,
        EthereumSignTx,
        EthereumSignTxEIP1559,
        EthereumSignTypedData,
    )

    from apps.common.keychain import (
        MsgOut,
        Handler,
    )

    # messages for "with_keychain_and_network_from_path" decorator
    MsgInKeychainNetworkPath = TypeVar(
        "MsgInKeychainNetworkPath",
        EthereumGetAddress,
        EthereumSignMessage,
    )

    HandlerWithKeychainAndNetworkFromPath = Callable[
        [Context, MsgInKeychainNetworkPath, Keychain, EthereumNetworkInfo],
        Awaitable[MsgOut],
    ]

    HandlerWithKeychainAndDefsFromPath = Callable[
        [Context, EthereumSignTypedData, Keychain, definitions.Definitions],
        Awaitable[MsgOut],
    ]

    # messages for "with_keychain_and_defs_from_chain_id" decorator
    MsgInKeychainChainId = TypeVar(
        "MsgInKeychainChainId", EthereumSignTx, EthereumSignTxEIP1559
    )

    HandlerWithKeychainAndDefsFromChainId = Callable[
        [Context, MsgInKeychainChainId, Keychain, definitions.Definitions],
        Awaitable[MsgOut],
    ]


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
    patterns: Iterable[str],
    address_n: paths.Bip32Path,
    network_info: EthereumNetworkInfo,
) -> Iterable[paths.PathSchema]:
    if len(address_n) < 2:
        return ()

    slip44_hardened = address_n[1]

    def _get_hardened_slip44_networks():
        if network_info is not networks.UNKNOWN_NETWORK:
            yield network_info.slip44 | paths.HARDENED
        yield from networks.all_slip44_ids_hardened()

    # check with networks
    if slip44_hardened not in _get_hardened_slip44_networks():
        return ()

    if not slip44_hardened & paths.HARDENED:
        return ()

    slip44_id = slip44_hardened - paths.HARDENED
    schemas = [paths.PathSchema.parse(pattern, slip44_id) for pattern in patterns]
    return [s.copy() for s in schemas]


def with_keychain_and_network_from_path(
    *patterns: str,
) -> Callable[
    [HandlerWithKeychainAndNetworkFromPath[MsgInKeychainNetworkPath, MsgOut]],
    Handler[MsgInKeychainNetworkPath, MsgOut],
]:
    def decorator(
        func: HandlerWithKeychainAndNetworkFromPath[MsgInKeychainNetworkPath, MsgOut]
    ) -> Handler[MsgInKeychainNetworkPath, MsgOut]:
        async def wrapper(ctx: Context, msg: MsgInKeychainNetworkPath) -> MsgOut:
            # make sure that "network"'s slip44 is equal to the one present in "address_n"
            slip44 = (msg.address_n[1] & 0x7FFF_FFFF) if len(msg.address_n) > 2 else 0
            network = networks.by_slip44(slip44) or networks.UNKNOWN_NETWORK

            if network is networks.UNKNOWN_NETWORK and msg.encoded_network:
                network = definitions.get_and_check_definition(
                    msg.encoded_network, EthereumNetworkInfo
                )
                if network.slip44 != slip44:
                    network = networks.UNKNOWN_NETWORK

            schemas = _schemas_from_address_n(patterns, msg.address_n, network)
            keychain = await get_keychain(ctx, CURVE, schemas)
            with keychain:
                return await func(ctx, msg, keychain, network)

        return wrapper

    return decorator


def with_keychain_and_defs_from_path(
    *patterns: str,
) -> Callable[
    [HandlerWithKeychainAndDefsFromPath[MsgOut]],
    Handler[EthereumSignTypedData, MsgOut],
]:
    def decorator(
        func: HandlerWithKeychainAndDefsFromPath[MsgOut],
    ) -> Handler[EthereumSignTypedData, MsgOut]:
        async def wrapper(ctx: Context, msg: EthereumSignTypedData) -> MsgOut:
            defs = definitions.get_definitions_from_msg(msg)
            schemas = _schemas_from_address_n(patterns, msg.address_n, defs.network)
            keychain = await get_keychain(ctx, CURVE, schemas)
            with keychain:
                return await func(ctx, msg, keychain, defs)

        return wrapper

    return decorator


def _schemas_from_network(
    network_info: EthereumNetworkInfo,
) -> Iterable[paths.PathSchema]:
    slip44_id: tuple[int, ...]
    if network_info is networks.UNKNOWN_NETWORK:
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


def with_keychain_and_defs_from_chain_id(
    func: HandlerWithKeychainAndDefsFromChainId[MsgInKeychainChainId, MsgOut]
) -> Handler[MsgInKeychainChainId, MsgOut]:
    # this is only for SignTx, and only PATTERN_ADDRESS is allowed
    async def wrapper(ctx: Context, msg: MsgInKeychainChainId) -> MsgOut:
        defs = definitions.get_definitions_from_msg(msg)
        schemas = _schemas_from_network(defs.network)
        keychain = await get_keychain(ctx, CURVE, schemas)
        with keychain:
            return await func(ctx, msg, keychain, defs)

    return wrapper
