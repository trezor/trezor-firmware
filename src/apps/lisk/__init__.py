from trezor import wire
from trezor.messages import MessageType


def boot():
    wire.add(MessageType.LiskGetPublicKey, __name__, "get_public_key")
    wire.add(MessageType.LiskGetAddress, __name__, "get_address")
    wire.add(MessageType.LiskSignMessage, __name__, "sign_message")
    wire.add(MessageType.LiskVerifyMessage, __name__, "verify_message")
    wire.add(MessageType.LiskSignTx, __name__, "sign_tx")
