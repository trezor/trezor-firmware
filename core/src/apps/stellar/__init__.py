from trezor import wire
from trezor.messages import MessageType

from apps.common.paths import PATTERN_SEP5

CURVE = "ed25519"
SLIP44_ID = 148
PATTERN = PATTERN_SEP5


def boot() -> None:
    wire.add(MessageType.StellarGetAddress, __name__, "get_address")
    wire.add(MessageType.StellarSignTx, __name__, "sign_tx")
