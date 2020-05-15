from trezor import wire
from trezor.messages import MessageType


def boot() -> None:
    wire.add(MessageType.GetEntropy, __name__, "get_entropy")
    wire.add(MessageType.SignIdentity, __name__, "sign_identity")
    wire.add(MessageType.GetECDHSessionKey, __name__, "get_ecdh_session_key")
    wire.add(MessageType.CipherKeyValue, __name__, "cipher_key_value")
