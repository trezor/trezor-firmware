from trezor.messages.MessageType import TezosGetAddress, TezosGetPublicKey, TezosSignTx
from trezor.wire import protobuf_workflow, register


def dispatch_TezosGetAddress(*args, **kwargs):
    from .get_address import tezos_get_address

    return tezos_get_address(*args, **kwargs)


def dispatch_TezosSignTx(*args, **kwargs):
    from .sign_tx import tezos_sign_tx

    return tezos_sign_tx(*args, **kwargs)


def dispatch_TezosGetPublicKey(*args, **kwargs):
    from .get_public_key import tezos_get_public_key

    return tezos_get_public_key(*args, **kwargs)


def boot():
    register(TezosGetAddress, protobuf_workflow, dispatch_TezosGetAddress)
    register(TezosSignTx, protobuf_workflow, dispatch_TezosSignTx)
    register(TezosGetPublicKey, protobuf_workflow, dispatch_TezosGetPublicKey)
