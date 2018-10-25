from trezor.utils import HashWriter

from apps.monero.xmr import crypto
from apps.monero.xmr.serialize import int_serialize


class KeccakXmrArchive:
    def __init__(self, ctx=None):
        self.kwriter = get_keccak_writer(ctx)

    def get_digest(self):
        return self.kwriter.get_digest()

    def buffer(self, buf):
        return self.kwriter.write(buf)

    def uvarint(self, i):
        int_serialize.dump_uvarint(self.kwriter, i)

    def uint(self, i, width):
        int_serialize.dump_uint(self.kwriter, i, width)


def get_keccak_writer(ctx=None):
    if ctx is None:
        ctx = crypto.get_keccak()
    return HashWriter(ctx)
