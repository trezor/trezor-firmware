from .state import HandshakeState
from .functions.dh import DH


class NoiseProtocol:
    handshake_state: HandshakeState
    dh_fn: DH
