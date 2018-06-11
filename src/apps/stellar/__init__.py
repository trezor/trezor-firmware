from trezor.wire import register, protobuf_workflow
from trezor.messages.wire_types import StellarGetAddress
from trezor.messages.wire_types import StellarGetPublicKey
from trezor.messages.wire_types import StellarSignTx


def dispatch_StellarGetAddress(*args, **kwargs):
    from .get_address import get_address
    return get_address(*args, **kwargs)


def dispatch_StellarGetPublicKey(*args, **kwargs):
    from .get_public_key import get_public_key
    return get_public_key(*args, **kwargs)


def dispatch_StellarSignTx(*args, **kwargs):
    from .sign_tx import sign_tx
    return sign_tx(*args, **kwargs)


def boot():
    register(StellarGetAddress, protobuf_workflow, dispatch_StellarGetAddress)
    register(StellarGetPublicKey, protobuf_workflow, dispatch_StellarGetPublicKey)
    register(StellarSignTx, protobuf_workflow, dispatch_StellarSignTx)
