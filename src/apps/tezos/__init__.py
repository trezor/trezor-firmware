from trezor import wire
from trezor.messages import MessageType


def boot():
    wire.add(MessageType.TezosGetAddress, __name__, "get_address")
    wire.add(MessageType.TezosSignTx, __name__, "sign_tx")
    wire.add(MessageType.TezosGetPublicKey, __name__, "get_public_key")
