from trezor import wire
from trezor.messages import MessageType

CURVE = "secp256k1"


def boot() -> None:
    wire.add(MessageType.EthereumGetAddress, __name__, "get_address")
    wire.add(MessageType.EthereumGetPublicKey, __name__, "get_public_key")
    wire.add(MessageType.EthereumSignTx, __name__, "sign_tx")
    wire.add(MessageType.EthereumSignMessage, __name__, "sign_message")
    wire.add(MessageType.EthereumVerifyMessage, __name__, "verify_message")
