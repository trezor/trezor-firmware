from trezor import utils, wire
from trezor.messages.RequestType import TXFINISHED
from trezor.messages.SignTx import SignTx
from trezor.messages.TxAck import TxAck
from trezor.messages.TxRequest import TxRequest

from apps.common import coininfo, paths, seed

from ..keychain import with_keychain
from . import bitcoin, helpers, layout, progress

if not utils.BITCOIN_ONLY:
    from . import bitcoinlike, decred, zcash

if False:
    from typing import Type, Union


BITCOIN_NAMES = ("Bitcoin", "Regtest", "Testnet")


@with_keychain
async def sign_tx(
    ctx: wire.Context, msg: SignTx, keychain: seed.Keychain, coin: coininfo.CoinInfo
) -> TxRequest:
    if not utils.BITCOIN_ONLY:
        if coin.decred:
            signer_class = decred.Decred  # type: Type[bitcoin.Bitcoin]
        elif coin.overwintered:
            signer_class = zcash.Overwintered
        elif coin.coin_name not in BITCOIN_NAMES:
            signer_class = bitcoinlike.Bitcoinlike
        else:
            signer_class = bitcoin.Bitcoin

    else:
        signer_class = bitcoin.Bitcoin

    signer = signer_class(msg, keychain, coin).signer()

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
