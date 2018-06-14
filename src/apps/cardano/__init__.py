from trezor.messages.MessageType import (
    CardanoGetAddress,
    CardanoGetPublicKey,
    CardanoSignMessage,
    CardanoSignTransaction,
    CardanoVerifyMessage,
)
from trezor.wire import protobuf_workflow, register


def dispatch_CardanoGetAddress(*args, **kwargs):
    from .get_address import cardano_get_address

    return cardano_get_address(*args, **kwargs)


def dispatch_CardanoGetPublicKey(*args, **kwargs):
    from .get_public_key import cardano_get_public_key

    return cardano_get_public_key(*args, **kwargs)


def dispatch_CardanoSignMessage(*args, **kwargs):
    from .sign_message import cardano_sign_message

    return cardano_sign_message(*args, **kwargs)


def dispatch_CardanoSignTransaction(*args, **kwargs):
    from .sign_transaction import cardano_sign_transaction

    return cardano_sign_transaction(*args, **kwargs)


def dispatch_CardanoVerifyMessage(*args, **kwargs):
    from .verify_message import cardano_verify_message

    return cardano_verify_message(*args, **kwargs)


def boot():
    register(CardanoGetAddress, protobuf_workflow, dispatch_CardanoGetAddress)
    register(CardanoGetPublicKey, protobuf_workflow, dispatch_CardanoGetPublicKey)
    register(CardanoSignMessage, protobuf_workflow, dispatch_CardanoSignMessage)
    register(CardanoVerifyMessage, protobuf_workflow, dispatch_CardanoVerifyMessage)
    register(CardanoSignTransaction, protobuf_workflow, dispatch_CardanoSignTransaction)
