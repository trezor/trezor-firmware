from trezor import wire
from trezor.messages import MessageType

from apps.common.paths import PATTERN_SEP5

CURVE = "ed25519"
SLIP44_ID = 134
PATTERN = PATTERN_SEP5


def boot() -> None:
    wire.add(MessageType.LiskGetPublicKey, __name__, "get_public_key")
    wire.add(MessageType.LiskGetAddress, __name__, "get_address")
    wire.add(MessageType.LiskSignTx, __name__, "sign_tx")
    wire.add(MessageType.LiskSignMessage, __name__, "sign_message")
    wire.add(MessageType.LiskVerifyMessage, __name__, "verify_message")
