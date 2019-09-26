from trezor import wire
from trezor.messages import MessageType

# from apps.common import HARDENED

# CURVE = "secp256k1"


def boot() -> None:
    # ns = [[CURVE, HARDENED | 44, HARDENED | 1533]]
    wire.add(MessageType.BeamSignMessage, __name__, "sign_message")
    wire.add(MessageType.BeamVerifyMessage, __name__, "verify_message")
    wire.add(MessageType.BeamGetPublicKey, __name__, "get_public_key")
    wire.add(MessageType.BeamGetOwnerKey, __name__, "get_owner_key")
    wire.add(MessageType.BeamGenerateKey, __name__, "generate_key")
    wire.add(MessageType.BeamGenerateNonce, __name__, "generate_nonce")
    wire.add(MessageType.BeamGetNoncePublic, __name__, "get_nonce_public")
    wire.add(MessageType.BeamGenerateRangeproof, __name__, "generate_rangeproof")
    wire.add(MessageType.BeamSignTransaction, __name__, "sign_transaction")
