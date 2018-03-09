from trezor.wire import register, protobuf_workflow
from trezor.utils import unimport
from trezor.messages.wire_types import \
    GetPublicKey, GetAddress, \
    GetEntropy, \
    SignTx, \
    SignMessage, VerifyMessage, \
    SignIdentity, \
    GetECDHSessionKey, \
    CipherKeyValue


@unimport
def dispatch_GetPublicKey(*args, **kwargs):
    from .get_public_key import get_public_key
    return get_public_key(*args, **kwargs)


@unimport
def dispatch_GetAddress(*args, **kwargs):
    from .get_address import get_address
    return get_address(*args, **kwargs)


@unimport
def dispatch_GetEntropy(*args, **kwargs):
    from .get_entropy import get_entropy
    return get_entropy(*args, **kwargs)


@unimport
def dispatch_SignTx(*args, **kwargs):
    from .sign_tx import sign_tx
    return sign_tx(*args, **kwargs)


@unimport
def dispatch_SignMessage(*args, **kwargs):
    from .sign_message import sign_message
    return sign_message(*args, **kwargs)


@unimport
def dispatch_VerifyMessage(*args, **kwargs):
    from .verify_message import verify_message
    return verify_message(*args, **kwargs)


@unimport
def dispatch_SignIdentity(*args, **kwargs):
    from .sign_identity import sign_identity
    return sign_identity(*args, **kwargs)


@unimport
def dispatch_GetECDHSessionKey(*args, **kwargs):
    from .ecdh import get_ecdh_session_key
    return get_ecdh_session_key(*args, **kwargs)


@unimport
def dispatch_CipherKeyValue(*args, **kwargs):
    from .cipher_key_value import cipher_key_value
    return cipher_key_value(*args, **kwargs)


def boot():
    register(GetPublicKey, protobuf_workflow, dispatch_GetPublicKey)
    register(GetAddress, protobuf_workflow, dispatch_GetAddress)
    register(GetEntropy, protobuf_workflow, dispatch_GetEntropy)
    register(SignTx, protobuf_workflow, dispatch_SignTx)
    register(SignMessage, protobuf_workflow, dispatch_SignMessage)
    register(VerifyMessage, protobuf_workflow, dispatch_VerifyMessage)
    register(SignIdentity, protobuf_workflow, dispatch_SignIdentity)
    register(GetECDHSessionKey, protobuf_workflow, dispatch_GetECDHSessionKey)
    register(CipherKeyValue, protobuf_workflow, dispatch_CipherKeyValue)
