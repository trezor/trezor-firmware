from trezor import wire
from trezor.messages import MessageType

from apps.common.paths import PATTERN_BIP44

CURVE = "secp256k1"
SLIP44_ID = 144
PATTERN = PATTERN_BIP44


def boot() -> None:
    wire.add(MessageType.RippleGetAddress, __name__, "get_address")
    wire.add(MessageType.RippleSignTx, __name__, "sign_tx")
