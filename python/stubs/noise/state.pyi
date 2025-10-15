import typing as t

Priv = t.TypeVar("Priv")
Pub = t.TypeVar("Pub")

from .functions.keypair import KeyPair

class HandshakeState(t.Generic[Priv, Pub]):
    s: KeyPair[Priv, Pub]
    e: KeyPair[Priv, Pub]
    rs: KeyPair[Priv, Pub]
    re: KeyPair[Priv, Pub]
