from typing import TYPE_CHECKING

from apps.common import paths
from apps.common.keychain import get_keychain

from . import CURVE, networks

if TYPE_CHECKING:
    from typing import Callable, Iterable, TypeVar

    from trezor.wire import Context

    from trezor.messages import (
        EthereumGetAddress,
        EthereumGetPublicKey,
        EthereumSignMessage,
        EthereumSignTx,
        EthereumSignTxEIP1559,
        EthereumSignTypedData,
    )

    from apps.common.keychain import MsgOut, Handler, HandlerWithKeychain

    EthereumMessages = (
        EthereumGetAddress
        | EthereumGetPublicKey
        | EthereumSignTx
        | EthereumSignMessage
        | EthereumSignTypedData
    )
    MsgIn = TypeVar("MsgIn", bound=EthereumMessages)

    EthereumSignTxAny = EthereumSignTx | EthereumSignTxEIP1559
    MsgInChainId = TypeVar("MsgInChainId", bound=EthereumSignTxAny)


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


def _schemas_from_address_n(
    patterns: Iterable[str], address_n: paths.Bip32Path
) -> Iterable[paths.PathSchema]:
    # Casa paths (purpose of 45) do not have hardened coin types
    if address_n[0] == 45 | paths.HARDENED and not address_n[1] & paths.HARDENED:
        slip44_hardened = address_n[1] | paths.HARDENED
    else:
        slip44_hardened = address_n[1]

    if slip44_hardened not in networks.all_slip44_ids_hardened():
        return ()

    if not slip44_hardened & paths.HARDENED:
        return ()

    slip44_id = slip44_hardened - paths.HARDENED
    schemas = [paths.PathSchema.parse(pattern, slip44_id) for pattern in patterns]
    return [s.copy() for s in schemas]


def with_keychain_from_path(
    *patterns: str,
) -> Callable[[HandlerWithKeychain[MsgIn, MsgOut]], Handler[MsgIn, MsgOut]]:
    def decorator(func: HandlerWithKeychain[MsgIn, MsgOut]) -> Handler[MsgIn, MsgOut]:
        async def wrapper(ctx: Context, msg: MsgIn) -> MsgOut:
            schemas = _schemas_from_address_n(patterns, msg.address_n)
            keychain = await get_keychain(ctx, CURVE, schemas)
            with keychain:
                return await func(ctx, msg, keychain)

        return wrapper

    return decorator


def _schemas_from_chain_id(msg: EthereumSignTxAny) -> Iterable[paths.PathSchema]:
    info = networks.by_chain_id(msg.chain_id)
    slip44_id: tuple[int, ...]
    if info is None:
        # allow Ethereum or testnet paths for unknown networks
        slip44_id = (60, 1)
    elif info.slip44 not in (60, 1):
        # allow cross-signing with Ethereum unless it's testnet
        slip44_id = (info.slip44, 60)
    else:
        slip44_id = (info.slip44,)

    schemas = [
        paths.PathSchema.parse(pattern, slip44_id) for pattern in PATTERNS_ADDRESS
    ]
    return [s.copy() for s in schemas]


def with_keychain_from_chain_id(
    func: HandlerWithKeychain[MsgInChainId, MsgOut]
) -> Handler[MsgInChainId, MsgOut]:
    # this is only for SignTx, and only PATTERN_ADDRESS is allowed
    async def wrapper(ctx: Context, msg: MsgInChainId) -> MsgOut:
        schemas = _schemas_from_chain_id(msg)
        keychain = await get_keychain(ctx, CURVE, schemas)
        with keychain:
            return await func(ctx, msg, keychain)

    return wrapper
