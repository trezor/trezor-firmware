import storage.cache
from trezor import wire
from trezor.messages.OwnershipProof import OwnershipProof
from trezor.messages.Preauthorized import Preauthorized
from trezor.messages.TxRequest import TxRequest

from .common import get_coin_by_name
from .get_ownership_proof import get_ownership_proof_impl
from .sign_tx import sign_tx_impl

if False:
    from typing import Union
    from .authorization import CoinJoinAuthorization


async def preauthorized(ctx, msg: Preauthorized) -> Union[TxRequest, OwnershipProof]:
    authorization = storage.cache.get(
        storage.cache.APP_BITCOIN_COINJOIN_AUTHORIZATION
    )  # type: CoinJoinAuthorization
    if not authorization:
        raise wire.ProcessError("Unauthorized operation")

    if msg.sign_tx:
        coin = get_coin_by_name(msg.sign_tx.coin_name)
        return await sign_tx_impl(
            ctx, msg.sign_tx, authorization.keychain, coin, authorization
        )
    elif msg.get_ownership_proof:
        coin = get_coin_by_name(msg.get_ownership_proof.coin_name)
        return await get_ownership_proof_impl(
            ctx, msg.get_ownership_proof, authorization.keychain, coin, authorization
        )
    else:
        raise wire.DataError("Unknown message")
