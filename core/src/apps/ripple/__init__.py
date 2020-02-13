from trezor import wire
from trezor.messages import MessageType

from apps.common import HARDENED

CURVE = "secp256k1"


def boot() -> None:
    ns = [[CURVE, HARDENED | 44, HARDENED | 144]]
    wire.add(MessageType.RippleGetAddress, __name__, "get_address", ns)
    wire.add(MessageType.RippleSignTx, __name__, "sign_tx", ns)
    wire.add(MessageType.RippleGetPublicKey, __name__, "get_public_key", ns)
