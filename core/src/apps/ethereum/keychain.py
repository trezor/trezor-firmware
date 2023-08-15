from typing import TYPE_CHECKING

from trezor.messages import EthereumNetworkInfo

from apps.common import paths
from apps.common.keychain import get_keychain

from . import CURVE, definitions, networks

if TYPE_CHECKING:
    from typing import Any, Awaitable, Callable, Iterable, TypeVar

    from trezor.messages import (
        EthereumGetAddress,
        EthereumSignMessage,
        EthereumSignTx,
        EthereumSignTxEIP1559,
        EthereumSignTypedData,
    )

    from apps.common.keychain import Handler, Keychain, MsgOut

    # messages for "with_keychain_and_network_from_path" decorator
    MsgInAddressN = TypeVar(
        "MsgInAddressN",
        EthereumGetAddress,
        EthereumSignMessage,
        EthereumSignTypedData,
    )

    HandlerAddressN = Callable[
        [MsgInAddressN, Keychain, definitions.Definitions],
        Awaitable[MsgOut],
    ]

    # messages for "with_keychain_and_defs_from_chain_id" decorator
    MsgInSignTx = TypeVar(
        "MsgInSignTx",
        EthereumSignTx,
        EthereumSignTxEIP1559,
    )

    HandlerChainId = Callable[
        [MsgInSignTx, Keychain, definitions.Definitions],
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
    paths.PATTERN_CASA,
)


def _slip44_from_address_n(address_n: paths.Bip32Path) -> int | None:
    HARDENED = paths.HARDENED  # local_cache_attribute
    if len(address_n) < 2:
        return None

    if address_n[0] == 45 | HARDENED and not address_n[1] & HARDENED:
        return address_n[1]

    return address_n[1] & ~HARDENED


def _defs_from_message(
    msg: Any, chain_id: int | None = None, slip44: int | None = None
) -> definitions.Definitions:
    encoded_network = None
    encoded_token = None

    # try to get both from msg.definitions
    if hasattr(msg, "definitions"):
        if msg.definitions is not None:
            encoded_network = msg.definitions.encoded_network
            encoded_token = msg.definitions.encoded_token

    elif hasattr(msg, "encoded_network"):
        encoded_network = msg.encoded_network

    return definitions.Definitions.from_encoded(
        encoded_network, encoded_token, chain_id, slip44
    )


def _schemas_from_network(
    patterns: Iterable[str],
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

    schemas = [paths.PathSchema.parse(pattern, slip44_id) for pattern in patterns]
    return [s.copy() for s in schemas]


def with_keychain_from_path(
    *patterns: str,
) -> Callable[[HandlerAddressN[MsgInAddressN, MsgOut]], Handler[MsgInAddressN, MsgOut]]:
    def decorator(
        func: HandlerAddressN[MsgInAddressN, MsgOut]
    ) -> Handler[MsgInAddressN, MsgOut]:
        async def wrapper(msg: MsgInAddressN) -> MsgOut:
            slip44 = _slip44_from_address_n(msg.address_n)
            defs = _defs_from_message(msg, slip44=slip44)
            schemas = _schemas_from_network(patterns, defs.network)
            keychain = await get_keychain(CURVE, schemas)
            with keychain:
                return await func(msg, keychain, defs)

        return wrapper

    return decorator


def with_keychain_from_chain_id(
    func: HandlerChainId[MsgInSignTx, MsgOut]
) -> Handler[MsgInSignTx, MsgOut]:
    # this is only for SignTx, and only PATTERN_ADDRESS is allowed
    async def wrapper(msg: MsgInSignTx) -> MsgOut:
        defs = _defs_from_message(msg, chain_id=msg.chain_id)
        schemas = _schemas_from_network(PATTERNS_ADDRESS, defs.network)
        keychain = await get_keychain(CURVE, schemas)
        with keychain:
            return await func(msg, keychain, defs)

    return wrapper
