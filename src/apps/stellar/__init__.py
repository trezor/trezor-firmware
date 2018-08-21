from trezor.messages.MessageType import StellarGetAddress, StellarSignTx
from trezor.wire import protobuf_workflow, register


def dispatch_StellarGetAddress(*args, **kwargs):
    from .get_address import get_address

    return get_address(*args, **kwargs)


def dispatch_StellarSignTx(*args, **kwargs):
    from .sign_tx import sign_tx

    return sign_tx(*args, **kwargs)


def boot():
    register(StellarGetAddress, protobuf_workflow, dispatch_StellarGetAddress)
    register(StellarSignTx, protobuf_workflow, dispatch_StellarSignTx)
