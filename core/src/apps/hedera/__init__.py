from trezor import wire
from trezor.messages import MessageType

from apps.common.paths import PATTERN_BIP44

CURVE = "ed25519"
SLIP44_ID = 3030
PATTERN = PATTERN_BIP44


def boot() -> None:
    wire.add(MessageType.HederaGetPublicKey, __name__, "get_pk")
    wire.add(MessageType.HederaSignTx, __name__, "sign_tx")
