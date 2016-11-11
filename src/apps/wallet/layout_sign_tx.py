from trezor.utils import unimport
from trezor import wire


async def confirm_output(output):
    return True


async def confirm_total(total_out, fee):
    return True


@unimport
async def layout_sign_tx(message, session_id):
    from ..common.seed import get_root_node
    from ..common import signtx

    from trezor.messages import RequestType
    from trezor.messages.TxRequest import TxRequest
    from trezor.messages.wire_types import TxAck

    root = await get_root_node(session_id)

    signer = signtx.sign_tx(message, root)
    res = None
    while True:
        try:
            req = signer.send(res)
        except signtx.SigningError as e:
            raise wire.FailureError(*e.args)
        if isinstance(req, TxRequest):
            if req.request_type == RequestType.TXFINISHED:
                break
            res = await wire.reply_message(session_id, req, TxAck)
        elif isinstance(req, signtx.UiConfirmOutput):
            res = await confirm_output(req.output)
        elif isinstance(req, signtx.UiConfirmTotal):
            res = await confirm_total(req.total_out, req.fee)
        else:
            raise ValueError('Invalid signing instruction')
    return req
