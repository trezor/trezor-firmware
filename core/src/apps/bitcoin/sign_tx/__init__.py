from trezor import utils, wire
from trezor.messages.RequestType import TXFINISHED
from trezor.messages.TxRequest import TxRequest

from ..common import BITCOIN_NAMES
from ..keychain import with_keychain
from . import approvers, bitcoin, helpers, progress

if not utils.BITCOIN_ONLY:
    from . import bitcoinlike, decred, zcash

if False:
    from typing import Optional, Union

    from protobuf import FieldCache

    from trezor.messages.SignTx import SignTx
    from trezor.messages.TxAckInput import TxAckInput
    from trezor.messages.TxAckOutput import TxAckOutput
    from trezor.messages.TxAckPrevMeta import TxAckPrevMeta
    from trezor.messages.TxAckPrevInput import TxAckPrevInput
    from trezor.messages.TxAckPrevOutput import TxAckPrevOutput
    from trezor.messages.TxAckPrevExtraData import TxAckPrevExtraData

    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain

    from ..authorization import CoinJoinAuthorization

    TxAckType = Union[
        TxAckInput,
        TxAckOutput,
        TxAckPrevMeta,
        TxAckPrevInput,
        TxAckPrevOutput,
        TxAckPrevExtraData,
    ]


@with_keychain
async def sign_tx(
    ctx: wire.Context,
    msg: SignTx,
    keychain: Keychain,
    coin: CoinInfo,
    authorization: Optional[CoinJoinAuthorization] = None,
) -> TxRequest:
    if authorization:
        approver: approvers.Approver = approvers.CoinJoinApprover(
            msg, coin, authorization
        )
    else:
        approver = approvers.BasicApprover(msg, coin)

    if utils.BITCOIN_ONLY or coin.coin_name in BITCOIN_NAMES:
        signer_class = bitcoin.Bitcoin
    else:
        if coin.decred:
            signer_class = decred.Decred
        elif coin.overwintered:
            signer_class = zcash.Zcashlike
        else:
            signer_class = bitcoinlike.Bitcoinlike

    signer = signer_class(msg, keychain, coin, approver).signer()

    res: Union[TxAckType, bool, None] = None
    field_cache: FieldCache = {}
    while True:
        req = signer.send(res)
        if isinstance(req, tuple):
            request_class, req = req
            assert isinstance(req, TxRequest)
            if req.request_type == TXFINISHED:
                return req
            res = await ctx.call(req, request_class, field_cache)
        elif isinstance(req, helpers.UiConfirm):
            res = await req.confirm_dialog(ctx)
            progress.report_init()
        else:
            raise TypeError("Invalid signing instruction")
