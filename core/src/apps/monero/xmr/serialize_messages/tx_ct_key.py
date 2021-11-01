class CtKey:
    __slots__ = ("dest", "mask")

    def __init__(self, dest, mask) -> None:
        self.dest = dest
        self.mask = mask
