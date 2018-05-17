from trezor.wire import register, protobuf_workflow
from trezor.messages.wire_types import StellarGetPublicKey
from trezor.messages.wire_types import StellarSignTx


def dispatch_StellarGetPublicKey(*args, **kwargs):
    from .get_public_key import get_public_key
    return get_public_key(*args, **kwargs)


def dispatch_StellarSignTx(*args, **kwargs):
    from .sign_tx import sign_tx_loop
    return sign_tx_loop(*args, **kwargs)


def boot():
    register(StellarGetPublicKey, protobuf_workflow, dispatch_StellarGetPublicKey)
    register(StellarSignTx, protobuf_workflow, dispatch_StellarSignTx)
