from trezor import wire
from trezor.messages import MessageType

from apps.common import HARDENED

CURVE = "secp256k1"
TRON_PUBLICKEY = "0492491c3f954d0a2a71e7f475e30ffbeb967aafde678f44a3a3264d813f498d954b3e000f4a71cbcdf4c97c609d3d207b75132aee66c0842dd8d0f6dd5054aa6c"


def boot():
    ns = [[CURVE, HARDENED | 44, HARDENED | 195]]
    wire.add(MessageType.TronGetAddress, __name__, "get_address", ns)
    wire.add(MessageType.TronSignTx, __name__, "sign_tx", ns)
