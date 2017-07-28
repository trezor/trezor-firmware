from trezor.wire import register, protobuf_workflow
from trezor.utils import unimport
from trezor.messages.wire_types import \
    GetPublicKey, GetAddress, \
    GetEntropy, \
    SignTx, \
    SignMessage, VerifyMessage, \
    SignIdentity, \
    CipherKeyValue


@unimport
def dispatch_GetPublicKey(*args, **kwargs):
    from .get_public_key import layout_get_public_key
    return layout_get_public_key(*args, **kwargs)


@unimport
def dispatch_GetAddress(*args, **kwargs):
    from .get_address import layout_get_address
    return layout_get_address(*args, **kwargs)


@unimport
def dispatch_GetEntropy(*args, **kwargs):
    from .get_entropy import layout_get_entropy
    return layout_get_entropy(*args, **kwargs)


@unimport
def dispatch_SignTx(*args, **kwargs):
    from .sign_tx import sign_tx
    return sign_tx(*args, **kwargs)


@unimport
def dispatch_SignMessage(*args, **kwargs):
    from .sign_message import layout_sign_message
    return layout_sign_message(*args, **kwargs)


@unimport
def dispatch_VerifyMessage(*args, **kwargs):
    from .verify_message import layout_verify_message
    return layout_verify_message(*args, **kwargs)


@unimport
def dispatch_SignIdentity(*args, **kwargs):
    from .sign_identity import layout_sign_identity
    return layout_sign_identity(*args, **kwargs)


@unimport
def dispatch_CipherKeyValue(*args, **kwargs):
    from .cipher_key_value import layout_cipher_key_value
    return layout_cipher_key_value(*args, **kwargs)


def boot():
    register(GetPublicKey, protobuf_workflow, dispatch_GetPublicKey)
    register(GetAddress, protobuf_workflow, dispatch_GetAddress)
    register(GetEntropy, protobuf_workflow, dispatch_GetEntropy)
    register(SignTx, protobuf_workflow, dispatch_SignTx)
    register(SignMessage, protobuf_workflow, dispatch_SignMessage)
    register(VerifyMessage, protobuf_workflow, dispatch_VerifyMessage)
    register(SignIdentity, protobuf_workflow, dispatch_SignIdentity)
    register(CipherKeyValue, protobuf_workflow, dispatch_CipherKeyValue)
