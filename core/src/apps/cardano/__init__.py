from trezor import wire
from trezor.messages import MessageType

from apps.common import HARDENED

CURVE = "ed25519"
SEED_NAMESPACE = [HARDENED | 44, HARDENED | 1815]


def boot() -> None:
    wire.add(MessageType.CardanoGetAddress, __name__, "get_address")
    wire.add(MessageType.CardanoGetPublicKey, __name__, "get_public_key")
    wire.add(MessageType.CardanoSignTx, __name__, "sign_tx")
