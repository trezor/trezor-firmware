from trezor.wire import register, protobuf_workflow
from trezor.messages.wire_types import \
    LiskGetAddress


def dispatch_LiskGetAddress(*args, **kwargs):
    from .get_address import layout_lisk_get_address
    return layout_lisk_get_address(*args, **kwargs)

def boot():
    register(LiskGetAddress, protobuf_workflow, dispatch_LiskGetAddress)
