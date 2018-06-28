from trezor.wire import register, protobuf_workflow
from trezor.messages.MessageType import RippleGetAddress
from trezor.messages.MessageType import RippleSignTx
from .get_address import get_address


def dispatch_RippleGetAddress(*args, **kwargs):
    from .get_address import get_address
    return get_address(*args, **kwargs)


def dispatch_RippleSignTx(*args, **kwargs):
    from .sign_tx import sign_tx
    return sign_tx(*args, **kwargs)


def boot():
    register(RippleGetAddress, protobuf_workflow, dispatch_RippleGetAddress)
    register(RippleSignTx, protobuf_workflow, dispatch_RippleSignTx)
