from trezor import wire

from apps.common import HARDENED, paths
from apps.common.keychain import get_keychain

from . import CURVE, networks

if False:
    from typing import Callable
    from typing_extensions import Protocol

    from protobuf import MessageType

    from trezor.messages.EthereumSignTx import EthereumSignTx

    from apps.common.keychain import MsgOut, Handler, HandlerWithKeychain

    class MsgWithAddressN(MessageType, Protocol):
        address_n = ...  # type: paths.Bip32Path


# We believe Ethereum should use 44'/60'/a' for everything, because it is
# account-based, rather than UTXO-based. Unfortunately, lot of Ethereum
# tools (MEW, Metamask) do not use such scheme and set a = 0 and then
# iterate the address index i. Therefore for compatibility reasons we use
# the same scheme: 44'/60'/0'/0/i and only the i is being iterated.

PATTERN_ADDRESS = "m/44'/coin_type'/0'/0/address_index"
PATTERN_PUBKEY = "m/44'/coin_type'/0'/*"


def _schema_from_address_n(
    pattern: str, address_n: paths.Bip32Path
) -> paths.PathSchema:
    if len(address_n) < 2:
        return paths.SCHEMA_NO_MATCH

    slip44_hardened = address_n[1]
    if slip44_hardened not in networks.all_slip44_ids_hardened():
        return paths.SCHEMA_NO_MATCH

    if not slip44_hardened & HARDENED:
        return paths.SCHEMA_ANY_PATH

    slip44_id = slip44_hardened - HARDENED
    return paths.PathSchema(pattern, slip44_id)


def with_keychain_from_path(
    pattern: str,
) -> Callable[
    [HandlerWithKeychain[MsgWithAddressN, MsgOut]], Handler[MsgWithAddressN, MsgOut]
]:
    def decorator(
        func: HandlerWithKeychain[MsgWithAddressN, MsgOut]
    ) -> Handler[MsgWithAddressN, MsgOut]:
        async def wrapper(ctx: wire.Context, msg: MsgWithAddressN) -> MsgOut:
            schema = _schema_from_address_n(pattern, msg.address_n)
            keychain = await get_keychain(ctx, CURVE, [schema])
            with keychain:
                return await func(ctx, msg, keychain)

        return wrapper

    return decorator


def _schema_from_chain_id(msg: EthereumSignTx) -> paths.PathSchema:
    if msg.chain_id is None:
        return _schema_from_address_n(PATTERN_ADDRESS, msg.address_n)

    info = networks.by_chain_id(msg.chain_id)
    if info is None:
        return paths.SCHEMA_NO_MATCH

    slip44_id = info.slip44
    if networks.is_wanchain(msg.chain_id, msg.tx_type):
        slip44_id = networks.SLIP44_WANCHAIN
    return paths.PathSchema(PATTERN_ADDRESS, slip44_id)


def with_keychain_from_chain_id(
    func: HandlerWithKeychain[EthereumSignTx, MsgOut]
) -> Handler[EthereumSignTx, MsgOut]:
    # this is only for SignTx, and only PATTERN_ADDRESS is allowed
    async def wrapper(ctx: wire.Context, msg: EthereumSignTx) -> MsgOut:
        schema = _schema_from_chain_id(msg)
        keychain = await get_keychain(ctx, CURVE, [schema])
        with keychain:
            return await func(ctx, msg, keychain)

    return wrapper
