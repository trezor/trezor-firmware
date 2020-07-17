from trezor import utils, wire
from trezor.messages.RequestType import TXFINISHED
from trezor.messages.SignTx import SignTx
from trezor.messages.TxAck import TxAck
from trezor.messages.TxRequest import TxRequest

from apps.common import coininfo, paths

from ..common import BITCOIN_NAMES
from ..keychain import with_keychain
from . import approvers, bitcoin, helpers, layout, progress

if not utils.BITCOIN_ONLY:
    from . import bitcoinlike, decred, zcash

if False:
    from typing import Optional, Union
    from apps.common.seed import Keychain
    from ..authorization import CoinJoinAuthorization


@with_keychain
async def sign_tx(
    ctx: wire.Context,
    msg: SignTx,
    keychain: Keychain,
    coin: coininfo.CoinInfo,
    authorization: Optional[CoinJoinAuthorization] = None,
) -> TxRequest:
    if authorization:
        approver = approvers.CoinJoinApprover(msg, coin, authorization)
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

    res = None  # type: Union[TxAck, bool, None]
    field_cache = {}
    while True:
        req = signer.send(res)
        if isinstance(req, TxRequest):
            if req.request_type == TXFINISHED:
                break
            res = await ctx.call(req, TxAck, field_cache)
        elif isinstance(req, helpers.UiConfirmOutput):
            res = await layout.confirm_output(ctx, req.output, req.coin)
            progress.report_init()
        elif isinstance(req, helpers.UiConfirmTotal):
            res = await layout.confirm_total(ctx, req.spending, req.fee, req.coin)
            progress.report_init()
        elif isinstance(req, helpers.UiConfirmJointTotal):
            res = await layout.confirm_joint_total(
                ctx, req.spending, req.total, req.coin
            )
            progress.report_init()
        elif isinstance(req, helpers.UiConfirmFeeOverThreshold):
            res = await layout.confirm_feeoverthreshold(ctx, req.fee, req.coin)
            progress.report_init()
        elif isinstance(req, helpers.UiConfirmChangeCountOverThreshold):
            res = await layout.confirm_change_count_over_threshold(
                ctx, req.change_count
            )
            progress.report_init()
        elif isinstance(req, helpers.UiConfirmNonDefaultLocktime):
            res = await layout.confirm_nondefault_locktime(ctx, req.lock_time)
            progress.report_init()
        elif isinstance(req, helpers.UiConfirmForeignAddress):
            res = await paths.show_path_warning(ctx, req.address_n)
            progress.report_init()
        else:
            raise TypeError("Invalid signing instruction")
    return req
