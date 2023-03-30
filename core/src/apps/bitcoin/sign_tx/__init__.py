from typing import TYPE_CHECKING

from trezor import utils

from ..keychain import with_keychain

if not utils.BITCOIN_ONLY:
    from . import bitcoinlike, decred, zcash_v4
    from apps.zcash.signer import Zcash

if TYPE_CHECKING:
    from typing import Protocol

    from trezor.wire import Context
    from trezor.messages import (
        SignTx,
        TxAckInput,
        TxAckOutput,
        TxAckPrevMeta,
        TxAckPrevInput,
        TxAckPrevOutput,
        TxAckPrevExtraData,
        TxRequest,
    )

    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain

    from . import approvers
    from ..authorization import CoinJoinAuthorization

    TxAckType = (
        TxAckInput
        | TxAckOutput
        | TxAckPrevMeta
        | TxAckPrevInput
        | TxAckPrevOutput
        | TxAckPrevExtraData
    )

    class SignerClass(Protocol):
        def __init__(  # pylint: disable=super-init-not-called
            self,
            tx: SignTx,
            keychain: Keychain,
            coin: CoinInfo,
            approver: approvers.Approver | None,
        ) -> None:
            ...

        async def signer(self) -> None:
            ...


@with_keychain
async def sign_tx(
    ctx: Context,
    msg: SignTx,
    keychain: Keychain,
    coin: CoinInfo,
    authorization: CoinJoinAuthorization | None = None,
) -> TxRequest:
    from trezor.enums import RequestType
    from trezor.messages import TxRequest

    from ..common import BITCOIN_NAMES
    from . import approvers, bitcoin, helpers, progress

    approver: approvers.Approver | None = None
    if authorization:
        approver = approvers.CoinJoinApprover(msg, coin, authorization)

    if utils.BITCOIN_ONLY or coin.coin_name in BITCOIN_NAMES:
        signer_class: type[SignerClass] = bitcoin.Bitcoin
    else:
        if coin.decred:
            signer_class = decred.Decred
        elif coin.overwintered:
            if msg.version == 5:
                signer_class = Zcash
            else:
                signer_class = zcash_v4.ZcashV4
        else:
            signer_class = bitcoinlike.Bitcoinlike

    signer = signer_class(msg, keychain, coin, approver).signer()

    res: TxAckType | bool | None = None
    while True:
        req = signer.send(res)
        if isinstance(req, tuple):
            request_class, req = req
            assert TxRequest.is_type_of(req)
            if req.request_type == RequestType.TXFINISHED:
                return req
            res = await ctx.call(req, request_class)
        elif isinstance(req, helpers.UiConfirm):
            res = await req.confirm_dialog(ctx)
            progress.progress.report_init()
        else:
            raise TypeError("Invalid signing instruction")
