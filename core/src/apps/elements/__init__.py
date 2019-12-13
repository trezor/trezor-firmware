from trezor import wire
from trezor.messages import MessageType


def boot() -> None:
    ns = [["slip21"]]
    wire.add(
        MessageType.ElementsGetRangeProofNonce, __name__, "get_rangeproof_nonce", ns
    )
