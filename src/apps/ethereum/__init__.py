from trezor.wire import register, protobuf_workflow
from trezor.utils import unimport
from trezor.messages.wire_types import \
    EthereumGetAddress


@unimport
def dispatch_EthereumGetAddress(*args, **kwargs):
    from .ethereum_get_address import layout_ethereum_get_address
    return layout_ethereum_get_address(*args, **kwargs)


def boot():
    register(EthereumGetAddress, protobuf_workflow, dispatch_EthereumGetAddress)
