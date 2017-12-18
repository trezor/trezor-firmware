from trezor.wire import register, protobuf_workflow
from trezor.utils import unimport
from trezor.messages.wire_types import \
    EthereumGetAddress, EthereumSignTx


@unimport
def dispatch_EthereumGetAddress(*args, **kwargs):
    from .ethereum_get_address import layout_ethereum_get_address
    return layout_ethereum_get_address(*args, **kwargs)


@unimport
def dispatch_EthereumSignTx(*args, **kwargs):
    from .ethereum_sign_tx import ethereum_sign_tx
    return ethereum_sign_tx(*args, **kwargs)


def boot():
    register(EthereumGetAddress, protobuf_workflow, dispatch_EthereumGetAddress)
    register(EthereumSignTx, protobuf_workflow, dispatch_EthereumSignTx)
