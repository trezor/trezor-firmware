from trezor.wire import register, protobuf_workflow
from trezor.messages.MessageType import NEMGetAddress, NEMSignTx


def dispatch_NemGetAddress(*args, **kwargs):
    from .get_address import get_address
    return get_address(*args, **kwargs)


def dispatch_NemSignTx(*args, **kwargs):
    from .signing import sign_tx
    return sign_tx(*args, **kwargs)


def boot():
    register(NEMGetAddress, protobuf_workflow, dispatch_NemGetAddress)
    register(NEMSignTx, protobuf_workflow, dispatch_NemSignTx)
