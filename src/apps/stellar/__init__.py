from trezor.wire import register, protobuf_workflow
from trezor.messages.wire_types import StellarGetPublicKey


def dispatch_StellarGetPublicKey(*args, **kwargs):
    from .get_public_key import get_public_key
    return get_public_key(*args, **kwargs)


def boot():
    register(StellarGetPublicKey, protobuf_workflow, dispatch_StellarGetPublicKey)
