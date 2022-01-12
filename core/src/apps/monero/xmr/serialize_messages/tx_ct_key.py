from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..crypto import Sc25519

class CtKey:
    __slots__ = ("dest", "mask")

    def __init__(self, dest: Sc25519, mask: Sc25519) -> None:
        self.dest = dest
        self.mask = mask
