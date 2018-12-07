from trezor import wire
from trezor.messages import MessageType

from apps.common import HARDENED


def boot():
    ns = [
        ["ed25519-keccak", HARDENED | 44, HARDENED | 43],
        ["ed25519-keccak", HARDENED | 44, HARDENED | 1],
    ]
    wire.add(MessageType.NEMGetAddress, __name__, "get_address", ns)
    wire.add(MessageType.NEMSignTx, __name__, "sign_tx", ns)
