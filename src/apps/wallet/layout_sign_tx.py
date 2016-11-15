from trezor.utils import unimport
from trezor import wire


def format_amount(amount, coin):
    return '%s %s' % (amount / 1e8, coin.coin_shortcut)


async def confirm_output(session_id, output, coin):
    from trezor import ui
    from trezor.ui.text import Text
    from trezor.messages.ButtonRequestType import ConfirmOutput
    from ..common.confirm import confirm

    content = Text('Confirm output', ui.ICON_RESET,
                   ui.BOLD, format_amount(output.amount, coin),
                   ui.NORMAL, 'to',
                   ui.MONO, output.address[0:17],
                   ui.MONO, output.address[17:])
    return await confirm(session_id, content, ConfirmOutput)


async def confirm_total(session_id, spending, fee, coin):
    from trezor import ui
    from trezor.ui.text import Text
    from trezor.messages.ButtonRequestType import SignTx
    from ..common.confirm import hold_to_confirm

    content = Text('Confirm transaction', ui.ICON_RESET,
                   'Sending: %s' % format_amount(spending, coin),
                   'Fee: %s' % format_amount(fee, coin))
    return await hold_to_confirm(session_id, content, SignTx)


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
            res = await confirm_output(session_id, req.output, req.coin)
        elif isinstance(req, signtx.UiConfirmTotal):
            res = await confirm_total(session_id, req.spending, req.fee, req.coin)
        else:
            raise ValueError('Invalid signing instruction')
    return req
