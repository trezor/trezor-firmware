from trezor import wire
from trezor.messages import MessageType

from apps.common.paths import PATTERN_SEP5

CURVE = "ed25519"
SLIP44_ID = 1729
PATTERNS = (
    PATTERN_SEP5,
    "m/44'/coin_type'/0'/account'",  # Ledger compatibility
)


def boot() -> None:
    wire.add(MessageType.TezosGetAddress, __name__, "get_address")
    wire.add(MessageType.TezosSignTx, __name__, "sign_tx")
    wire.add(MessageType.TezosGetPublicKey, __name__, "get_public_key")
