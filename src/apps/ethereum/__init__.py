from trezor import wire
from trezor.messages import MessageType

from apps.common import HARDENED
from apps.ethereum.networks import all_slip44_ids_hardened


def boot():
    ns = []
    for i in all_slip44_ids_hardened():
        ns.append(["secp256k1", HARDENED | 44, i])
    wire.add(MessageType.EthereumGetAddress, __name__, "get_address", ns)
    wire.add(MessageType.EthereumGetPublicKey, __name__, "get_public_key", ns)
    wire.add(MessageType.EthereumSignTx, __name__, "sign_tx", ns)
    wire.add(MessageType.EthereumSignMessage, __name__, "sign_message", ns)
    wire.add(MessageType.EthereumVerifyMessage, __name__, "verify_message")
