from trezor import wire
from trezor.messages import MessageType

CURVE = "secp256k1"
SLIP44_ID = 194


def boot() -> None:
    wire.add(MessageType.EosGetPublicKey, __name__, "get_public_key")
    wire.add(MessageType.EosSignTx, __name__, "sign_tx")
