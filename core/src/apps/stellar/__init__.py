from trezor import wire
from trezor.messages import MessageType

CURVE = "ed25519"
SLIP44_ID = 148


def boot() -> None:
    wire.add(MessageType.StellarGetAddress, __name__, "get_address")
    wire.add(MessageType.StellarSignTx, __name__, "sign_tx")
