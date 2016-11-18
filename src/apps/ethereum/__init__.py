from trezor.wire import register_type, protobuf_handler
from trezor.utils import unimport
from trezor.messages.wire_types import \
    EthereumGetAddress


@unimport
def dispatch_EthereumGetAddress(*args, **kwargs):
    from .layout_ethereum_get_address import layout_ethereum_get_address
    return layout_ethereum_get_address(*args, **kwargs)

def boot():
    register_type(EthereumGetAddress, protobuf_handler, dispatch_EthereumGetAddress)
