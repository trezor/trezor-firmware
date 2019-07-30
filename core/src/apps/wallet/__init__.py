from trezor import utils, wire
from trezor.messages import MessageType


def boot() -> None:
    ns = [
        ["curve25519"],
        ["ed25519"],
        ["ed25519-keccak"],
        ["nist256p1"],
        ["secp256k1"],
        ["secp256k1-decred"],
        ["secp256k1-groestl"],
        ["secp256k1-smart"],
    ]
    if not utils.BITCOIN_ONLY:
        ns.append(["slip21"])

    wire.add(MessageType.GetPublicKey, __name__, "get_public_key", ns)
    wire.add(MessageType.GetAddress, __name__, "get_address", ns)
    wire.add(MessageType.GetEntropy, __name__, "get_entropy")
    wire.add(MessageType.SignTx, __name__, "sign_tx", ns)
    wire.add(MessageType.SignMessage, __name__, "sign_message", ns)
    wire.add(MessageType.VerifyMessage, __name__, "verify_message")
    wire.add(MessageType.SignIdentity, __name__, "sign_identity", ns)
    wire.add(MessageType.GetECDHSessionKey, __name__, "get_ecdh_session_key", ns)
    wire.add(MessageType.CipherKeyValue, __name__, "cipher_key_value", ns)
