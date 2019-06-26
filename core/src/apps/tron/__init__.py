from trezor import wire
from trezor.messages import MessageType

from apps.common import HARDENED

CURVE = "secp256k1"


def boot():
    ns = [[CURVE, HARDENED | 44, HARDENED | 195]]
    wire.add(MessageType.TronGetAddress, __name__, "get_address", ns)
    wire.add(MessageType.TronSignTx, __name__, "sign_tx", ns)
