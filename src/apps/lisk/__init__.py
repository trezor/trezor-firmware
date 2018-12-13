from trezor import wire
from trezor.messages import MessageType

from apps.common import HARDENED


def boot():
    ns = [["ed25519", HARDENED | 44, HARDENED | 134]]
    wire.add(MessageType.LiskGetPublicKey, __name__, "get_public_key", ns)
    wire.add(MessageType.LiskGetAddress, __name__, "get_address", ns)
    wire.add(MessageType.LiskSignTx, __name__, "sign_tx", ns)
    wire.add(MessageType.LiskSignMessage, __name__, "sign_message", ns)
    wire.add(MessageType.LiskVerifyMessage, __name__, "verify_message")
