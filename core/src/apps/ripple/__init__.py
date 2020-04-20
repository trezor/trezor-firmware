from trezor import wire
from trezor.messages import MessageType

CURVE = "secp256k1"
SLIP44_ID = 144


def boot() -> None:
    wire.add(MessageType.RippleGetAddress, __name__, "get_address")
    wire.add(MessageType.RippleSignTx, __name__, "sign_tx")
