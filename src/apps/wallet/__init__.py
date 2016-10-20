from trezor.wire import register_type, protobuf_handler
from trezor.utils import unimport
from trezor.messages.wire_types import \
    GetPublicKey, GetAddress, SignMessage


@unimport
def dispatch_GetPublicKey(*args, **kwargs):
    from .layout_get_public_key import layout_get_public_key
    return layout_get_public_key(*args, **kwargs)


@unimport
def dispatch_GetAddress(*args, **kwargs):
    from .layout_get_address import layout_get_address
    return layout_get_address(*args, **kwargs)


@unimport
def dispatch_SignMessage(*args, **kwargs):
    from .layout_sign_message import layout_sign_message
    return layout_sign_message(*args, **kwargs)


def boot():
    register_type(GetPublicKey, protobuf_handler, dispatch_GetPublicKey)
    register_type(GetAddress, protobuf_handler, dispatch_GetAddress)
    register_type(SignMessage, protobuf_handler, dispatch_SignMessage)
