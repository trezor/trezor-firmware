from trezor import wire
from trezor.messages import MessageType


def boot():
    wire.add(MessageType.NEMGetAddress, __name__, "get_address")
    wire.add(MessageType.NEMSignTx, __name__, "sign_tx")
