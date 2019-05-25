from trezor import wire
from trezor.messages import MessageType

from apps.common import HARDENED

CURVE = "nist256p1"


def boot() -> None:
    ns = [
        [CURVE, HARDENED | 44, HARDENED | 1024],
        [CURVE, HARDENED | 44, HARDENED | 888],
    ]
    wire.add(MessageType.OntologyGetPublicKey, __name__, "get_public_key", ns)
    wire.add(MessageType.OntologyGetAddress, __name__, "get_address", ns)
    wire.add(MessageType.OntologySignTx, __name__, "sign_tx", ns)
