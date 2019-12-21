from trezor import wire
from trezor.messages import MessageType

from apps.common import HARDENED

CURVE = "ed25519-keccak"

def boot() -> None:
    ns = [[CURVE, HARDENED | 44, HARDENED | 43], [CURVE, HARDENED | 44, HARDENED | 1]]
    wire.add(MessageType.NEM2GetPublicKey, __name__, "get_public_key", ns)
    wire.add(MessageType.NEM2SignTx, __name__, "sign_tx", ns)
    wire.add(MessageType.NEM2EncryptMessage, __name__, "encrypt_message", ns)
    wire.add(MessageType.NEM2DecryptMessage, __name__, "decrypt_message", ns)
