from ubinascii import hexlify

from trezor import io
from trezor.crypto import chacha20poly1305, random

from apps.common import seed

MAGIC = b"TRAD"
VERSION = 1


def _get_seed_id() -> bytes:
    n = seed.derive_slip21_node_without_passphrase(["seed_id"])
    return n.key()


def _get_appdata_node(name: str) -> bytes:
    return seed.derive_slip21_node_without_passphrase(["SdAppData", name])


class SdAppData:
    def __init__(self, name: str):
        self.sd = io.SDCard()
        self.sd.power(True)
        self.fs = io.FatFS()
        self.fs.mount()
        self.fs.mkdir("/trezor", True)
        seed_id = _get_seed_id()[:16]
        seed_dir = "/trezor/seed_%s" % hexlify(seed_id).decode()
        self.fs.mkdir(seed_dir, True)
        self.fs.mkdir("%s/appdata" % seed_dir, True)
        self.dir = "%s/appdata/%s" % (seed_dir, name)
        self.fs.mkdir(self.dir, True)
        self.node = _get_appdata_node(name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.fs.unmount()
        self.sd.power(False)

    def _key_to_filename_enckey(self, key: bytes) -> (str, str, bytes):
        n0 = self.node.clone()
        n0.derive_path([key])
        n = n0.clone()
        n.derive_path(["fn"])
        fnkey = n.key()
        n = n0.clone()
        n.derive_path(["enc"])
        enckey = n.key()
        fn = hexlify(fnkey[:20]).decode()
        prefix = "%s/%s" % (self.dir, fn[:2])
        fullpath = "%s/%s" % (prefix, fn[2:])
        return prefix, fullpath, enckey

    def get(self, key: bytes) -> bytes:
        _, fullpath, enckey = self._key_to_filename_enckey(key)
        try:
            s = self.fs.stat(fullpath)
        except OSError:
            raise KeyError
        buf = bytearray(s[0])
        with self.fs.open(fullpath, "r") as f:
            f.read(buf)
        if buf[:4] != MAGIC:
            raise ValueError("Invalid magic")
        if buf[4:8] != VERSION.to_bytes(4, "big"):
            raise ValueError("Invalid version")
        nonce = buf[8:20]
        ctx = chacha20poly1305(enckey, nonce)
        ctx.auth(fullpath)
        value = ctx.decrypt(buf[20:-16])
        tag = ctx.finish()
        if tag != buf[-16:]:
            raise ValueError("Invalid MAC")
        return value

    def set(self, key: bytes, value: bytes) -> None:
        prefix, fullpath, enckey = self._key_to_filename_enckey(key)
        self.fs.mkdir(prefix, True)
        nonce = random.bytes(12)
        ctx = chacha20poly1305(enckey, nonce)
        ctx.auth(fullpath)
        enc = ctx.encrypt(value)
        tag = ctx.finish()
        with self.fs.open(fullpath, "w") as f:
            f.write(MAGIC)
            f.write(VERSION.to_bytes(4, "big"))
            f.write(nonce)
            f.write(enc)
            f.write(tag)

    def delete(self, key: bytes) -> None:
        _, fullpath, _ = self._key_to_filename_enckey(key)
        self.fs.unlink(fullpath)
