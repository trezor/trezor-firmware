from trezor.wire import register, protobuf_workflow
from trezor.messages.wire_types import \
    LiskGetAddress, LiskSignTx, LiskGetPublicKey, LiskSignMessage, LiskVerifyMessage


def dispatch_LiskGetAddress(*args, **kwargs):
    from .get_address import layout_lisk_get_address
    return layout_lisk_get_address(*args, **kwargs)


def dispatch_LiskGetPublicKey(*args, **kwargs):
    from .get_public_key import lisk_get_public_key
    return lisk_get_public_key(*args, **kwargs)


def dispatch_LiskSignTx(*args, **kwargs):
    from .sign_tx import lisk_sign_tx
    return lisk_sign_tx(*args, **kwargs)


def dispatch_LiskSignMessage(*args, **kwargs):
    from .sign_message import lisk_sign_message
    return lisk_sign_message(*args, **kwargs)


def dispatch_LiskVerifyMessage(*args, **kwargs):
    from .verify_message import lisk_verify_message
    return lisk_verify_message(*args, **kwargs)


def boot():
    register(LiskGetPublicKey, protobuf_workflow, dispatch_LiskGetPublicKey)
    register(LiskGetAddress, protobuf_workflow, dispatch_LiskGetAddress)
    register(LiskSignMessage, protobuf_workflow, dispatch_LiskSignMessage)
    register(LiskVerifyMessage, protobuf_workflow, dispatch_LiskVerifyMessage)
    register(LiskSignTx, protobuf_workflow, dispatch_LiskSignTx)
