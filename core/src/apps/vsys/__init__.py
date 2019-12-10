from trezor import wire
from trezor.messages import MessageType

from apps.common import HARDENED

CURVE = "curve25519"


def boot() -> None:
    ns = [[CURVE, HARDENED | 44, HARDENED | 360], [CURVE, HARDENED | 44, HARDENED | 1]]
    wire.add(MessageType.VsysGetAddress, __name__, "get_address", ns)
    wire.add(MessageType.VsysSignTx, __name__, "sign_tx", ns)
    wire.add(MessageType.VsysGetPublicKey, __name__, "get_public_key", ns)
