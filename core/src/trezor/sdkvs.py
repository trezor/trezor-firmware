from ubinascii import hexlify

from trezor import io
from trezor.crypto import chacha20poly1305, hmac, random
from trezor.crypto.hashlib import sha256

from apps.common import storage

MAGIC = b"TRKV"
VERSION = 1


def _get_seed_dir() -> bytes:
    return "/trezor/seed_%s" % storage.device.get_seed_id()


class SdKvs:
    def __init__(self, name: str):
        self.sd = io.SDCard()
        self.sd.power(True)
        self.fs = io.FatFS()
        self.fs.mount()
        self.fs.mkdir("/trezor", True)
        seed_dir = _get_seed_dir()
        self.fs.mkdir(seed_dir, True)
        self.fs.mkdir("%s/kvs" % seed_dir, True)
        self.dir = "%s/kvs/%s" % (seed_dir, name)
        self.fs.mkdir(self.dir, True)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.fs.unmount()
        self.sd.power(False)

    def _key_to_fname(self, key: bytes) -> str:
        h = hexlify(hmac.new(key, MAGIC, sha256).digest()).decode()[:40]
        fn = "%s/%s/%s" % (self.dir, h[:2], h[2:])
        return fn

    def _derive_enckey(self, fn: str) -> bytes:
        # TODO: derive symmetric key from master seed
        return sha256(fn).digest()

    def get(self, key: bytes) -> bytes:
        fn = self._key_to_fname(key)
        try:
            s = self.fs.stat(fn)
        except OSError:
            raise KeyError
        buf = bytearray(s[0])
        with self.fs.open(fn, "r") as f:
            f.read(buf)
        if buf[:4] != MAGIC:
            raise ValueError("Invalid magic")
        if buf[4:8] != VERSION.to_bytes(4, "big"):
            raise ValueError("Invalid version")
        enckey = self._derive_enckey(fn)
        nonce = buf[8:20]
        ctx = chacha20poly1305(enckey, nonce)
        ctx.auth(fn)
        data = ctx.decrypt(buf[20:-16])
        tag = ctx.finish()
        if tag != buf[-16:]:
            raise ValueError("Invalid MAC")
        return data

    def put(self, key: bytes, data: bytes) -> None:
        fn = self._key_to_fname(key)
        self.fs.mkdir(fn[:-39], True)  # create prefix directory
        enckey = self._derive_enckey(fn)
        nonce = random.bytes(12)
        ctx = chacha20poly1305(enckey, nonce)
        ctx.auth(fn)
        enc = ctx.encrypt(data)
        tag = ctx.finish()
        with self.fs.open(fn, "w") as f:
            f.write(MAGIC)
            f.write(VERSION.to_bytes(4, "big"))
            f.write(nonce)
            f.write(enc)
            f.write(tag)

    def delete(self, key: bytes) -> None:
        fn = self._key_to_fname(key)
        self.fs.unlink(fn)
