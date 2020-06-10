from trezor import wire
from trezor.messages import MessageType

CURVE = "ed25519-keccak"
SLIP44_ID = 43


def boot() -> None:
    wire.add(MessageType.NEMGetAddress, __name__, "get_address")
    wire.add(MessageType.NEMSignTx, __name__, "sign_tx")
