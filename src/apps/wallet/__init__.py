from trezor.wire import register_type, protobuf_handler
from trezor.utils import unimport
from trezor.messages.wire_types import \
    GetPublicKey, GetAddress, SignTx, EstimateTxSize, SignMessage


@unimport
def dispatch_GetPublicKey(*args, **kwargs):
    from .layout_get_public_key import layout_get_public_key
    return layout_get_public_key(*args, **kwargs)


@unimport
def dispatch_GetAddress(*args, **kwargs):
    from .layout_get_address import layout_get_address
    return layout_get_address(*args, **kwargs)


@unimport
def dispatch_SignTx(*args, **kwargs):
    from .layout_sign_tx import layout_sign_tx
    return layout_sign_tx(*args, **kwargs)


@unimport
async def dispatch_EstimateTxSize(msg, session_id):
    from trezor.messages.TxSize import TxSize
    m = TxSize()
    m.tx_size =  10 + msg.inputs_count * 149 + msg.outputs_count * 35
    return m


@unimport
def dispatch_SignMessage(*args, **kwargs):
    from .layout_sign_message import layout_sign_message
    return layout_sign_message(*args, **kwargs)


def boot():
    register_type(GetPublicKey, protobuf_handler, dispatch_GetPublicKey)
    register_type(GetAddress, protobuf_handler, dispatch_GetAddress)
    register_type(SignTx, protobuf_handler, dispatch_SignTx)
    register_type(EstimateTxSize, protobuf_handler, dispatch_EstimateTxSize)
    register_type(SignMessage, protobuf_handler, dispatch_SignMessage)
