from trezor import wire
from trezor.messages import MessageType

from apps.common import HARDENED

CURVE = "ed25519"


def boot() -> None:
    ns = [[CURVE, HARDENED | 44, HARDENED | 1729]]
    wire.add(MessageType.TezosGetAddress, __name__, "get_address", ns)
    wire.add(MessageType.TezosSignTx, __name__, "sign_tx", ns)
    wire.add(MessageType.TezosGetPublicKey, __name__, "get_public_key", ns)
