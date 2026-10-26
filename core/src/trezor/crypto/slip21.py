from typing import TYPE_CHECKING

from trezor.crypto import hmac

if TYPE_CHECKING:
    from buffer_types import AnyBytes
    from collections.abc import Sequence

    Slip21Path = Sequence[AnyBytes]


class Slip21Node:
    """
    This class implements the SLIP-0021 hierarchical derivation of symmetric keys, see
    https://github.com/satoshilabs/slips/blob/master/slip-0021.md.
    """

    def __init__(self, seed: bytes | None = None, data: bytes | None = None) -> None:
        assert seed is None or data is None, "Specify exactly one of: seed, data"
        if data is not None:
            self.data = data
        elif seed is not None:
            self.data = hmac(hmac.SHA512, b"Symmetric key seed", seed).digest()
        else:
            raise ValueError  # neither seed nor data specified

    def __del__(self) -> None:
        del self.data

    def derive_path(self, path: Slip21Path) -> None:
        for label in path:
            h = hmac(hmac.SHA512, self.data[0:32], b"\x00")
            h.update(label)
            self.data = h.digest()

    def key(self) -> bytes:
        return self.data[32:64]

    def clone(self) -> "Slip21Node":
        return Slip21Node(data=self.data)
