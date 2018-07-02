from trezor.wire import register, protobuf_workflow
from trezor.messages.MessageType import EthereumGetAddress, EthereumSignTx
from trezor.messages.MessageType import EthereumSignMessage, EthereumVerifyMessage


def dispatch_EthereumGetAddress(*args, **kwargs):
    from .get_address import ethereum_get_address
    return ethereum_get_address(*args, **kwargs)


def dispatch_EthereumSignTx(*args, **kwargs):
    from .sign_tx import ethereum_sign_tx
    return ethereum_sign_tx(*args, **kwargs)


def dispatch_EthereumSignMessage(*args, **kwargs):
    from .sign_message import ethereum_sign_message
    return ethereum_sign_message(*args, **kwargs)


def dispatch_EthereumVerifyMessage(*args, **kwargs):
    from .verify_message import ethereum_verify_message
    return ethereum_verify_message(*args, **kwargs)


def boot():
    register(EthereumGetAddress, protobuf_workflow, dispatch_EthereumGetAddress)
    register(EthereumSignTx, protobuf_workflow, dispatch_EthereumSignTx)
    register(EthereumSignMessage, protobuf_workflow, dispatch_EthereumSignMessage)
    register(EthereumVerifyMessage, protobuf_workflow, dispatch_EthereumVerifyMessage)
