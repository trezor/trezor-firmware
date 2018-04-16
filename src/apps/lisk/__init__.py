from trezor.wire import register, protobuf_workflow
from trezor.messages.wire_types import \
    LiskGetAddress, LiskGetPublicKey


def dispatch_LiskGetAddress(*args, **kwargs):
    from .get_address import layout_lisk_get_address
    return layout_lisk_get_address(*args, **kwargs)


def dispatch_LiskGetPublicKey(*args, **kwargs):
    from .get_public_key import lisk_get_public_key
    return lisk_get_public_key(*args, **kwargs)


def boot():
    register(LiskGetPublicKey, protobuf_workflow, dispatch_LiskGetPublicKey)
    register(LiskGetAddress, protobuf_workflow, dispatch_LiskGetAddress)
