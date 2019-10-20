from trezor import wire
from trezor.messages import MessageType

from apps.common import HARDENED

CURVE = "secp256k1"


def boot() -> None:
    ns = [[CURVE, HARDENED | 44, HARDENED | 714]]
    wire.add(MessageType.BinanceGetAddress, __name__, "get_address", ns)
    wire.add(MessageType.BinanceGetPublicKey, __name__, "get_public_key", ns)
    wire.add(MessageType.BinanceSignTx, __name__, "sign_tx", ns)
