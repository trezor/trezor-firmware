from trezor import wire
from trezor.messages import MessageType


def boot():
    wire.add(MessageType.CardanoGetAddress, __name__, "get_address")
    wire.add(MessageType.CardanoGetPublicKey, __name__, "get_public_key")
    wire.add(MessageType.CardanoSignTx, __name__, "sign_transaction")
