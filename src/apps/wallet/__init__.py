from trezor.wire import register_type, protobuf_handler
from trezor.utils import unimport
from trezor.messages.wire_types import \
    GetPublicKey, GetAddress, SignTx, EstimateTxSize, \
    SignMessage, VerifyMessage, \
    SignIdentity, \
    CipherKeyValue


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
    from ..common.signtx import estimate_tx_size
    m = TxSize()
    m.tx_size = estimate_tx_size(msg.inputs_count, msg.outputs_count)
    return m


@unimport
def dispatch_SignMessage(*args, **kwargs):
    from .layout_sign_message import layout_sign_message
    return layout_sign_message(*args, **kwargs)


@unimport
def dispatch_VerifyMessage(*args, **kwargs):
    from .layout_verify_message import layout_verify_message
    return layout_verify_message(*args, **kwargs)


@unimport
def dispatch_SignIdentity(*args, **kwargs):
    from .layout_sign_identity import layout_sign_identity
    return layout_sign_identity(*args, **kwargs)


@unimport
def dispatch_CipherKeyValue(*args, **kwargs):
    from .layout_cipherkeyvalue import layout_cipherkeyvalue
    return layout_cipherkeyvalue(*args, **kwargs)


def boot():
    register_type(GetPublicKey, protobuf_handler, dispatch_GetPublicKey)
    register_type(GetAddress, protobuf_handler, dispatch_GetAddress)
    register_type(SignTx, protobuf_handler, dispatch_SignTx)
    register_type(EstimateTxSize, protobuf_handler, dispatch_EstimateTxSize)
    register_type(SignMessage, protobuf_handler, dispatch_SignMessage)
    register_type(VerifyMessage, protobuf_handler, dispatch_VerifyMessage)
    register_type(SignIdentity, protobuf_handler, dispatch_SignIdentity)
    register_type(CipherKeyValue, protobuf_handler, dispatch_CipherKeyValue)
