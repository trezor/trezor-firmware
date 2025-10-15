import typing as t
import typing_extensions as tx

Priv = t.TypeVar("Priv")
Pub = t.TypeVar("Pub")

class KeyPair(t.Generic[Priv, Pub]):
    private: Priv
    public: Pub
    public_bytes: bytes

    @classmethod
    def from_private_bytes(cls, private_bytes: bytes) -> tx.Self: ...
