from trezor import wire
from trezor.messages import MessageType

from apps.common import HARDENED


def boot():
    ns = [["ed25519", HARDENED | 44, HARDENED | 148]]
    wire.add(MessageType.StellarGetAddress, __name__, "get_address", ns)
    wire.add(MessageType.StellarSignTx, __name__, "sign_tx", ns)
