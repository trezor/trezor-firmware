from trezor import wire
from trezor.messages import MessageType


def boot():
    wire.add(MessageType.StellarGetAddress, __name__, "get_address")
    wire.add(MessageType.StellarSignTx, __name__, "sign_tx")
