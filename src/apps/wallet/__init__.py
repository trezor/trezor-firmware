from trezor import wire
from trezor.messages import MessageType


def boot():
    wire.add(MessageType.GetPublicKey, __name__, "get_public_key")
    wire.add(MessageType.GetAddress, __name__, "get_address")
    wire.add(MessageType.GetEntropy, __name__, "get_entropy")
    wire.add(MessageType.SignTx, __name__, "sign_tx")
    wire.add(MessageType.SignMessage, __name__, "sign_message")
    wire.add(MessageType.VerifyMessage, __name__, "verify_message")
    wire.add(MessageType.SignIdentity, __name__, "sign_identity")
    wire.add(MessageType.GetECDHSessionKey, __name__, "get_ecdh_session_key")
    wire.add(MessageType.CipherKeyValue, __name__, "cipher_key_value")
