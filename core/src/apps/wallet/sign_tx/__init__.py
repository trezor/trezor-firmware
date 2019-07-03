from trezor import utils, wire
from trezor.messages.RequestType import TXFINISHED
from trezor.messages.TxAck import TxAck
from trezor.messages.TxRequest import TxRequest

from apps.common import paths
from apps.wallet.sign_tx import (
    addresses,
    helpers,
    layout,
    multisig,
    progress,
    scripts,
    segwit_bip143,
    signing,
)


async def sign_tx(ctx, msg, keychain):
    signer = signing.sign_tx(msg, keychain)

    res = None
    while True:
        try:
            req = signer.send(res)
        except (
            signing.SigningError,
            multisig.MultisigError,
            addresses.AddressError,
            scripts.ScriptsError,
            segwit_bip143.Bip143Error,
        ) as e:
            raise wire.Error(*e.args)
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
