from trezor import wire
from trezor.messages import MessageType

from apps.common import HARDENED

CURVE = "ed25519-keccak"


def boot() -> None:
    ns = [[CURVE, HARDENED | 44, HARDENED | 43], [CURVE, HARDENED | 44, HARDENED | 1]]
    wire.add(MessageType.NEMGetAddress, __name__, "get_address", ns)
    wire.add(MessageType.NEMSignTx, __name__, "sign_tx", ns)
