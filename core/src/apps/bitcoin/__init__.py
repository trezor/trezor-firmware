from trezor import wire
from trezor.messages import MessageType


def boot() -> None:
    wire.add(MessageType.AuthorizeCoinJoin, __name__, "authorize_coinjoin")
    wire.add(MessageType.GetPublicKey, __name__, "get_public_key")
    wire.add(MessageType.GetAddress, __name__, "get_address")
    wire.add(MessageType.GetOwnershipId, __name__, "get_ownership_id")
    wire.add(MessageType.GetOwnershipProof, __name__, "get_ownership_proof")
    wire.add(MessageType.SignTx, __name__, "sign_tx")
    wire.add(MessageType.SignMessage, __name__, "sign_message")
    wire.add(MessageType.VerifyMessage, __name__, "verify_message")
