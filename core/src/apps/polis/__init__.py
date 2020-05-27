from trezor import wire
from trezor.messages import MessageType

CURVE = "bls12_381"
SLIP44_ID = 1997

def boot() -> None:
    wire.add(MessageType.PolisGetAddress, __name__, "get_address")
    wire.add(MessageType.PolisGetPublicKey, __name__, "get_public_key")
