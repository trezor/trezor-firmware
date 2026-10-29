# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezorcrypto import (
    SecretOwner,
    _secret_owner_activate,
    bip32,
    revoke_secrets,
    secbytes,
)

from trezor.crypto.curve import secp256k1

# These setup values are already exposed Python bytes; secure ingress is pending.
SEED = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
MASTER = bytes.fromhex(
    "e8f32e723decf4051aefac8e2c93c9c5b214313817cdb01a1494b917c8436b35"
)
DIGEST = b"\x42" * 32


class TestSecbytes(unittest.TestCase):
    def setUp(self):
        from trezor import config

        config.init()
        config.wipe()
        self.assertTrue(config.unlock("", None))
        revoke_secrets()
        _secret_owner_activate(SecretOwner())

    def tearDown(self):
        revoke_secrets()

    def assert_opaque(self, key):
        self.assertIsInstance(key, secbytes)
        for convert in (bytes, bytearray, memoryview, list):
            with self.assertRaises(TypeError):
                convert(key)
        with self.assertRaises(TypeError):
            key[0]  # pylint: disable=pointless-statement
        with self.assertRaises(TypeError):
            key[:]  # pylint: disable=pointless-statement
        with self.assertRaises(AttributeError):
            key.hex()
        with self.assertRaises(AttributeError):
            key.handle  # pylint: disable=pointless-statement
        self.assertEqual(repr(key), "<secbytes>")
        self.assertEqual(str(key), "<secbytes>")
        self.assertEqual("%s" % key, "<secbytes>")  # pylint: disable=consider-using-f-string
        self.assertEqual("{}".format(key), "<secbytes>")  # pylint: disable=consider-using-f-string

    def test_access_and_destroy(self):
        key = secbytes(MASTER, secbytes.SECP256K1)
        self.assert_opaque(key)
        self.assertEqual(secp256k1.sign(key, DIGEST), secp256k1.sign(MASTER, DIGEST))
        key.destroy()
        key.destroy()
        self.assert_opaque(key)
        with self.assertRaises(ValueError):
            secp256k1.sign(key, DIGEST)

    def test_snapshot_and_parent_destruction(self):
        node = bip32.from_seed(SEED, "secp256k1")
        key = node.private_key()
        node.derive(0x80000000)
        node.derive_path([1, 2])
        clone = node.clone()
        self.assertEqual(node.public_key(), clone.public_key())
        self.assertEqual(secp256k1.sign(key, DIGEST), secp256k1.sign(MASTER, DIGEST))
        node.__del__()
        node.__del__()
        self.assertEqual(secp256k1.sign(key, DIGEST), secp256k1.sign(MASTER, DIGEST))
        with self.assertRaises(ValueError):
            node.public_key()
        self.assertTrue(
            secp256k1.verify(
                clone.public_key(), secp256k1.sign(clone.private_key(), DIGEST), DIGEST
            )
        )

    def test_revoke_suspended_user(self):
        node = bip32.from_seed(SEED, "secp256k1")
        key = node.private_key()

        def suspended():
            yield key
            return secp256k1.sign(key, DIGEST)

        task = suspended()
        next(task)
        # Owner teardown must work without closing or unwinding the generator.
        revoke_secrets()
        with self.assertRaises(ValueError):
            task.send(None)
        with self.assertRaises(ValueError):
            node.clone()
        self.assert_opaque(key)
        _secret_owner_activate(SecretOwner())
        replacement = secbytes(MASTER, secbytes.SECP256K1)
        key.destroy()  # stale cleanup cannot destroy the replacement
        self.assertEqual(
            secp256k1.sign(replacement, DIGEST), secp256k1.sign(MASTER, DIGEST)
        )

    def test_errors_and_revocation(self):
        with self.assertRaises(TypeError):
            secp256k1.sign(SecretOwner(), DIGEST)
        key = secbytes(MASTER, secbytes.SECP256K1)
        with self.assertRaises(ValueError):
            secp256k1.sign(key, b"short")
        # An error does not silently destroy independently owned input values.
        self.assertEqual(secp256k1.sign(key, DIGEST), secp256k1.sign(MASTER, DIGEST))
        values = [secbytes(MASTER, secbytes.SECP256K1) for _ in range(65)]
        revoke_secrets()
        # Revocation reaches every blob, wherever the client keeps it.
        for value in values:
            with self.assertRaises(ValueError):
                secp256k1.sign(value, DIGEST)
        _secret_owner_activate(SecretOwner())
        self.assertEqual(
            secp256k1.sign(secbytes(MASTER, secbytes.SECP256K1), DIGEST),
            secp256k1.sign(MASTER, DIGEST),
        )

    def test_dead_clone(self):
        node = bip32.from_seed(SEED, "secp256k1")
        node.__del__()
        with self.assertRaises(ValueError):
            node.clone()
        live = bip32.from_seed(SEED, "secp256k1")
        revoke_secrets()
        with self.assertRaises(ValueError):
            live.clone()

    def test_no_capacity_limit(self):
        # Kernel memory does not grow with live secrets: a SignTx with many
        # change outputs keeps one derived node per output alive until GC.
        root = bip32.from_seed(SEED, "secp256k1")
        nodes = []
        for i in range(100):
            n = root.clone()
            n.derive(i)
            nodes.append(n)
        keys = [n.private_key() for n in nodes]
        self.assertEqual(len(keys), 100)
        expected = secp256k1.sign(keys[99], DIGEST)
        self.assertEqual(secp256k1.sign(nodes[99], DIGEST), expected)
        # Snapshots are independent of the node they came from.
        nodes[99].__del__()
        self.assertEqual(secp256k1.sign(keys[99], DIGEST), expected)

    def test_constructor_copy(self):
        source = bytearray(MASTER)
        key = secbytes(source, secbytes.SECP256K1)
        source[:] = b"\x00" * 32
        self.assertEqual(secp256k1.sign(key, DIGEST), secp256k1.sign(MASTER, DIGEST))

    def test_wrong_receiver(self):
        key = secbytes(MASTER, secbytes.SECP256K1)
        node = bip32.from_seed(SEED, "secp256k1")
        with self.assertRaises(TypeError):
            secbytes.destroy(node)
        with self.assertRaises(TypeError):
            bip32.HDNode.private_key(key)
        with self.assertRaises(TypeError):
            bip32.HDNode.__del__(key)

    def test_public_node(self):
        node = bip32.from_seed(SEED, "secp256k1")
        public = bip32.HDNode(
            depth=node.depth(),
            fingerprint=node.fingerprint(),
            child_num=node.child_num(),
            chain_code=node.chain_code(),
            public_key=node.public_key(),
            curve_name="secp256k1",
        )
        node.derive(1)
        public.derive(1, True)
        self.assertEqual(node.public_key(), public.public_key())
        self.assertEqual(
            node.serialize_public(0x0488B21E), public.serialize_public(0x0488B21E)
        )

    def test_holder_take(self):
        holder = secbytes(None)
        self.assertTrue(holder.empty())
        self.assert_opaque(holder)
        with self.assertRaises(ValueError):
            secp256k1.sign(holder, DIGEST)
        first = secbytes(MASTER, secbytes.SECP256K1)
        holder.take(first)
        self.assertFalse(holder.empty())
        self.assertTrue(first.empty())
        self.assertEqual(secp256k1.sign(holder, DIGEST), secp256k1.sign(MASTER, DIGEST))
        with self.assertRaises(ValueError):
            secp256k1.sign(first, DIGEST)
        # Taking a new value erases the previous one.
        holder.take(holder)
        holder.take(secbytes(b"\x01" * 32, secbytes.SECP256K1))
        self.assertNotEqual(
            secp256k1.sign(holder, DIGEST), secp256k1.sign(MASTER, DIGEST)
        )
        holder.destroy()
        self.assertTrue(holder.empty())
        with self.assertRaises(TypeError):
            holder.take(SecretOwner())

    def test_compact_sizes_and_moves(self):
        # Exercise every supported allocation size and moves in both directions.
        # No allocation is permitted during moves or destruction.
        import micropython
        from trezorcrypto import retain_secret

        holder = secbytes(None)
        for length in range(1, 161):
            source = secbytes(b"x" * length)
            micropython.heap_lock()
            try:
                holder.take(source)
                moved = source.empty()
                source.take(holder)
                returned = holder.empty()
                source.destroy()
                destroyed = source.empty()
            finally:
                micropython.heap_unlock()
            self.assertTrue(moved and returned and destroyed)

        # Retaining a compact record must preserve its tag and length.
        session = SecretOwner()
        request = SecretOwner(session)
        _secret_owner_activate(request)
        key = secbytes(MASTER, secbytes.SECP256K1)
        retain_secret(key)
        request.destroy()
        _secret_owner_activate(SecretOwner(session))
        self.assertEqual(secp256k1.sign(key, DIGEST), secp256k1.sign(MASTER, DIGEST))

    def test_bounded_holder(self):
        holder = secbytes(None, 32)
        holder.take(secbytes(MASTER, secbytes.SECP256K1))
        larger = secbytes(b"x" * 64)
        with self.assertRaises(ValueError):
            holder.take(larger)
        self.assertFalse(larger.empty())
        self.assertEqual(secp256k1.sign(holder, DIGEST), secp256k1.sign(MASTER, DIGEST))
        # A shorter move must erase the previous tag and trailing ciphertext.
        holder.take(secbytes(b"x", secbytes.SEED))
        node = bip32.from_seed(holder, "secp256k1")
        self.assertEqual(
            node.public_key(), bip32.from_seed(b"x", "secp256k1").public_key()
        )
        holder.take(secbytes(None, 0))
        self.assertTrue(holder.empty())
        for invalid in (-1, 161):
            with self.assertRaises(ValueError):
                secbytes(None, invalid)
        # A populated value takes a key type, and 32 is none.
        with self.assertRaises(ValueError):
            secbytes(MASTER, 32)

    def test_compact_heap_footprint(self):
        import gc

        # Compare batches so list/object headers cancel out. Values and holders
        # must save exactly 128/96 bytes on both 16- and 32-byte GC blocks.
        for length, saving in ((32, 128), (64, 96)):
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
                values[i] = secbytes(None, length)
            gc.collect()
            compact = gc.mem_alloc() - before
            # Conservative GC may retain a few temporary words from a native
            # frame. Allow two emulator GC blocks, far below one lost value.
            self.assertTrue(abs(full - compact - 16 * saving) <= 64)
            for i in range(16):
                values[i] = None

    def test_compact_node_heap_footprint(self):
        import gc

        root = bip32.from_seed(SEED, "secp256k1")
        root.public_key()
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
            values[i] = root.clone()
        gc.collect()
        compact = gc.mem_alloc() - before
        # The node encoding includes Cardano's private-key extension while
        # avoiding native padding and pointers. It stays below a full holder.
        self.assertTrue(compact < full)
        for node in values:
            self.assertEqual(node.public_key(), root.public_key())

    def test_owner_renew(self):
        with self.assertRaises(ValueError):
            SecretOwner(SecretOwner(), False)
        owner = SecretOwner(None, False)
        self.assertFalse(owner.valid())
        with self.assertRaises(ValueError):
            SecretOwner(owner)
        owner.renew()
        self.assertTrue(owner.valid())
        child = SecretOwner(owner)
        _secret_owner_activate(child)
        key = secbytes(MASTER, secbytes.SECP256K1)
        # Renewing erases the old identity and everything beneath it.
        owner.renew()
        self.assertTrue(owner.valid())
        self.assertFalse(child.valid())
        with self.assertRaises(ValueError):
            secp256k1.sign(key, DIGEST)
        with self.assertRaises(ValueError):
            owner.renew(owner)
        owner.destroy()
        self.assertFalse(owner.valid())

    def test_holders_do_not_allocate(self):
        import gc

        owner = SecretOwner(None, False)
        holder = secbytes(None)
        for _ in range(3):  # warm up method lookups and the vault
            owner.renew()
            _secret_owner_activate(SecretOwner(owner))
            holder.take(secbytes(MASTER, secbytes.SECP256K1))
            owner.destroy()
        gc.collect()
        before = gc.mem_free()
        for _ in range(10):
            owner.renew()
            _secret_owner_activate(SecretOwner(owner))
            holder.take(secbytes(MASTER, secbytes.SECP256K1))
            owner.destroy()
        gc.collect()
        # Only short-lived objects are created; nothing survives a collection.
        self.assertTrue(gc.mem_free() >= before)

    def test_options(self):
        key = secbytes(MASTER, secbytes.SECP256K1)
        for compressed in (True, False):
            self.assertEqual(
                secp256k1.sign(key, DIGEST, compressed),
                secp256k1.sign(MASTER, DIGEST, compressed),
            )


if __name__ == "__main__":
    unittest.main()
