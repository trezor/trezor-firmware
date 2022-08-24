from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .. import crypto


class CtKey:
    __slots__ = ("dest", "mask")

    def __init__(self, dest: crypto.Scalar, mask: crypto.Scalar) -> None:
        self.dest = dest
        self.mask = mask
