from trezor import wire
from trezor.messages import MessageType


def boot():
    wire.add(MessageType.RippleGetAddress, __name__, "get_address")
    wire.add(MessageType.RippleSignTx, __name__, "sign_tx")
