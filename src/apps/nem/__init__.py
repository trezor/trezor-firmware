from trezor.wire import register, protobuf_workflow
from trezor.utils import unimport
from trezor.messages.wire_types import NEMGetAddress, NEMSignTx


@unimport
def dispatch_NemGetAddress(*args, **kwargs):
    from .get_address import nem_get_address
    return nem_get_address(*args, **kwargs)


@unimport
def dispatch_NemSignTx(*args, **kwargs):
    from .signing import nem_sign_tx
    return nem_sign_tx(*args, **kwargs)


def boot():
    register(NEMGetAddress, protobuf_workflow, dispatch_NemGetAddress)
    register(NEMSignTx, protobuf_workflow, dispatch_NemSignTx)
