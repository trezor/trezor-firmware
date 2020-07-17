from trezor import utils, wire
from trezor.messages.RequestType import TXFINISHED
from trezor.messages.SignTx import SignTx
from trezor.messages.TxAck import TxAck
from trezor.messages.TxRequest import TxRequest

from apps.common import coininfo, paths

from ..keychain import get_keychain_for_coin
from . import approvers, bitcoin, helpers, layout, progress

if not utils.BITCOIN_ONLY:
    from . import bitcoinlike, decred, zcash

if False:
    from typing import Optional, Union
    from apps.common.seed import Keychain
    from ..authorization import CoinJoinAuthorization


BITCOIN_NAMES = ("Bitcoin", "Regtest", "Testnet")


async def sign_tx(ctx: wire.Context, msg: SignTx) -> TxRequest:
    keychain, coin = await get_keychain_for_coin(ctx, msg.coin_name)
    return await sign_tx_impl(ctx, msg, keychain, coin)


async def sign_tx_impl(
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
            signer_class = zcash.Overwintered
        else:
            signer_class = bitcoinlike.Bitcoinlike

    signer = signer_class(msg, keychain, coin, approver).signer()

    res = None  # type: Union[TxAck, bool, None]
    while True:
        req = signer.send(res)
        if isinstance(req, TxRequest):
            if req.request_type == TXFINISHED:
                break
            res = await ctx.call(req, TxAck)
        elif isinstance(req, helpers.UiConfirmOutput):
            mods = utils.unimport_begin()
            res = await layout.confirm_output(ctx, req.output, req.coin)
            utils.unimport_end(mods)
            progress.report_init()
        elif isinstance(req, helpers.UiConfirmTotal):
            mods = utils.unimport_begin()
            res = await layout.confirm_total(ctx, req.spending, req.fee, req.coin)
            utils.unimport_end(mods)
            progress.report_init()
        elif isinstance(req, helpers.UiConfirmJointTotal):
            mods = utils.unimport_begin()
            res = await layout.confirm_joint_total(
                ctx, req.spending, req.total, req.coin
            )
            utils.unimport_end(mods)
            progress.report_init()
        elif isinstance(req, helpers.UiConfirmFeeOverThreshold):
            mods = utils.unimport_begin()
            res = await layout.confirm_feeoverthreshold(ctx, req.fee, req.coin)
            utils.unimport_end(mods)
            progress.report_init()
        elif isinstance(req, helpers.UiConfirmChangeCountOverThreshold):
            mods = utils.unimport_begin()
            res = await layout.confirm_change_count_over_threshold(
                ctx, req.change_count
            )
            utils.unimport_end(mods)
            progress.report_init()
        elif isinstance(req, helpers.UiConfirmNonDefaultLocktime):
            mods = utils.unimport_begin()
            res = await layout.confirm_nondefault_locktime(ctx, req.lock_time)
            utils.unimport_end(mods)
            progress.report_init()
        elif isinstance(req, helpers.UiConfirmForeignAddress):
            mods = utils.unimport_begin()
            res = await paths.show_path_warning(ctx, req.address_n)
            utils.unimport_end(mods)
            progress.report_init()
        else:
            raise TypeError("Invalid signing instruction")
    return req
