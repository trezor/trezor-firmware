# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezorcrypto import (
    SecretOwner,
    _secret_owner_activate,
    retain_secret,
    revoke_secrets,
    secbytes,
)

from trezor import config


class TestEncryptedBytes(unittest.TestCase):
    def setUp(self):
        config.init()
        config.wipe()
        self.assertTrue(config.unlock("", None))
        revoke_secrets()
        self.session = SecretOwner()
        self.request = SecretOwner(self.session)
        _secret_owner_activate(self.request)

    def tearDown(self):
        revoke_secrets()

    def test_python_access(self):
        value = secbytes(b"\x42" * 32)
        for convert in (bytes, bytearray, memoryview, list):
            with self.assertRaises(TypeError):
                convert(value)
        with self.assertRaises(TypeError):
            value[0]
        with self.assertRaises(AttributeError):
            value.hex()
        self.assertEqual(repr(value), "<secbytes>")

    def test_move_and_destroy(self):
        value = secbytes(b"\x42" * 32)
        holder = secbytes(None, 32)
        holder.take(value)
        self.assertTrue(value.empty())
        self.assertFalse(holder.empty())
        holder.destroy()
        holder.destroy()
        self.assertTrue(holder.empty())

    def test_capacity_rejection_preserves_both(self):
        value = secbytes(b"\x42" * 64)
        holder = secbytes(None, 32)
        with self.assertRaises(ValueError):
            holder.take(value)
        self.assertTrue(holder.empty())
        self.assertFalse(value.empty())
        holder = secbytes(None, 64)
        holder.take(value)
        self.assertTrue(value.empty())

    def test_retained_value_survives_request(self):
        value = secbytes(b"\x42" * 32)
        retain_secret(value)
        self.request.destroy()
        _secret_owner_activate(SecretOwner(self.session))
        holder = secbytes(None, 32)
        holder.take(value)
        self.assertFalse(holder.empty())
        self.session.destroy()
        with self.assertRaises(ValueError):
            retain_secret(holder)

    def test_revocation_and_owner_reuse(self):
        value = secbytes(b"\x42" * 32)
        self.request.destroy()
        _secret_owner_activate(SecretOwner(self.session))
        with self.assertRaises(ValueError):
            retain_secret(value)
        replacement = secbytes(b"\x17" * 32)
        value.destroy()
        self.assertFalse(replacement.empty())

    def test_compact_heap_footprint(self):
        import gc

        values = [None] * 16
        gc.collect()
        before = gc.mem_alloc()
        for i in range(16):
            values[i] = secbytes(None)
        gc.collect()
        full = gc.mem_alloc() - before
        for i in range(16):
            values[i] = None
        gc.collect()
        before = gc.mem_alloc()
        for i in range(16):
            values[i] = secbytes(None, 32)
        gc.collect()
        compact = gc.mem_alloc() - before
        self.assertTrue(abs(full - compact - 16 * 128) <= 64)


if __name__ == "__main__":
    unittest.main()
