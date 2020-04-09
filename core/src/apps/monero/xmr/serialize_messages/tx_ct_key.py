class CtKey:
    __slots__ = ("dest", "mask")

    def __init__(self, dest, mask):
        self.dest = dest
        self.mask = mask
