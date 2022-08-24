from typing import TYPE_CHECKING

from trezor.utils import HashWriter

from apps.monero.xmr import crypto_helpers
from apps.monero.xmr.serialize import int_serialize

if TYPE_CHECKING:
    from trezor.utils import HashContext


class KeccakXmrArchive:
    def __init__(self, ctx: HashContext | None = None) -> None:
        self.kwriter = get_keccak_writer(ctx)

    def get_digest(self) -> bytes:
        return self.kwriter.get_digest()

    def buffer(self, buf: bytes) -> None:
        return self.kwriter.write(buf)

    def uvarint(self, i: int) -> None:
        int_serialize.dump_uvarint(self.kwriter, i)

    def uint(self, i: int, width: int) -> None:
        int_serialize.dump_uint(self.kwriter, i, width)


def get_keccak_writer(ctx: HashContext | None = None) -> HashWriter:
    if ctx is None:
        ctx = crypto_helpers.get_keccak()
    return HashWriter(ctx)
