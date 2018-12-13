from trezor import wire
from trezor.messages import MessageType

from apps.common import HARDENED


def boot():
    ns = [["secp256k1", HARDENED | 44, HARDENED | 60]]
    wire.add(MessageType.EthereumGetAddress, __name__, "get_address", ns)
    wire.add(MessageType.EthereumSignTx, __name__, "sign_tx", ns)
    wire.add(MessageType.EthereumSignMessage, __name__, "sign_message", ns)
    wire.add(MessageType.EthereumVerifyMessage, __name__, "verify_message")
