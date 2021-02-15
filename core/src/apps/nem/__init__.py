from trezor import wire
from trezor.messages import MessageType

from apps.common.paths import PATTERN_SEP5

CURVE = "ed25519-keccak"
SLIP44_ID = 43

PATTERNS = (
    PATTERN_SEP5,
    "m/44'/coin_type'/account'/0'/0'",  # NanoWallet compatibility
)


def boot() -> None:
    wire.add(MessageType.NEMGetAddress, __name__, "get_address")
    wire.add(MessageType.NEMSignTx, __name__, "sign_tx")
