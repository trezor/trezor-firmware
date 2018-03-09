from trezor.wire import register, protobuf_workflow
from trezor.utils import unimport
from trezor.messages.wire_types import NEMGetAddress


@unimport
def dispatch_NemGetAddress(*args, **kwargs):
    from .get_address import nem_get_address
    return nem_get_address(*args, **kwargs)


def boot():
    register(NEMGetAddress, protobuf_workflow, dispatch_NemGetAddress)
