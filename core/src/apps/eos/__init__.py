from trezor import wire
from trezor.messages import MessageType

from apps.common import HARDENED


def boot():
    ns = [["secp256k1", HARDENED | 44, HARDENED | 194]]

    wire.add(MessageType.EosGetPublicKey, __name__, "get_public_key", ns)
    wire.add(MessageType.EosSignTx, __name__, "sign_tx", ns)
