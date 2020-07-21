from trezor import wire

from apps.common import HARDENED, seed
from apps.common.keychain import get_keychain

from . import CURVE, networks

if False:
    from typing import List
    from typing_extensions import Protocol

    from protobuf import MessageType

    from trezor.messages.EthereumSignTx import EthereumSignTx

    from apps.common.keychain import MsgOut, Handler, HandlerWithKeychain

    class MsgWithAddressN(MessageType, Protocol):
        address_n = ...  # type: List[int]


async def from_address_n(ctx: wire.Context, address_n: List[int]) -> seed.Keychain:
    if len(address_n) < 2:
        raise wire.DataError("Forbidden key path")
    slip44_hardened = address_n[1]
    if slip44_hardened not in networks.all_slip44_ids_hardened():
        raise wire.DataError("Forbidden key path")
    namespace = [44 | HARDENED, slip44_hardened]
    return await get_keychain(ctx, CURVE, [namespace])


def with_keychain_from_path(
    func: HandlerWithKeychain[MsgWithAddressN, MsgOut]
) -> Handler[MsgWithAddressN, MsgOut]:
    async def wrapper(ctx: wire.Context, msg: MsgWithAddressN) -> MsgOut:
        keychain = await from_address_n(ctx, msg.address_n)
        with keychain:
            return await func(ctx, msg, keychain)

    return wrapper


def with_keychain_from_chain_id(
    func: HandlerWithKeychain[EthereumSignTx, MsgOut]
) -> Handler[EthereumSignTx, MsgOut]:
    async def wrapper(ctx: wire.Context, msg: EthereumSignTx) -> MsgOut:
        if msg.chain_id is None:
            keychain = await from_address_n(ctx, msg.address_n)
        else:
            info = networks.by_chain_id(msg.chain_id)
            if info is None:
                raise wire.DataError("Unsupported chain id")

            slip44 = info.slip44
            if networks.is_wanchain(msg.chain_id, msg.tx_type):
                slip44 = networks.SLIP44_WANCHAIN

            namespace = [44 | HARDENED, slip44 | HARDENED]
            keychain = await get_keychain(ctx, CURVE, [namespace])

        with keychain:
            return await func(ctx, msg, keychain)

    return wrapper
