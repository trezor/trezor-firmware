# flake8: noqa: F403,F405
from common import *  # isort:skip

import micropython
from trezorcrypto import (
    SecretOwner,
    _secret_owner_activate,
    _secret_task_enter,
    bip32,
    retain_secret,
    revoke_secrets,
    secbytes,
)

from trezor import loop
from trezor.crypto.curve import secp256k1

KEY = b"\x01" * 32
DIGEST = b"\x42" * 32


class TestSecretLifecycle(unittest.TestCase):
    def setUp(self):
        from trezor import config

        config.init()
        config.wipe()
        self.assertTrue(config.unlock("", None))
        loop.clear()
        revoke_secrets()

    def tearDown(self):
        loop.clear()
        revoke_secrets()

    def step(self, task):
        loop._queue.discard(task)
        loop._step(task, None)

    def root(self, task, parent=None, finalizer=None):
        session = parent or SecretOwner()
        owner = SecretOwner(session)
        loop.schedule(task, finalizer=finalizer, secret_owner=owner)
        return session, owner

    def assert_invalid(self, key):
        with self.assertRaises(ValueError):
            secp256k1.sign(key, DIGEST)

    def test_no_implicit_owner(self):
        with self.assertRaises(ValueError):
            secbytes(KEY)
        with self.assertRaises(ValueError):
            bip32.from_seed(KEY, "secp256k1")

    def test_owner_wrapper_allocation_failure(self):
        # Failed Python allocations must not consume kernel owner entries.
        for _ in range(80):
            failed = False
            micropython.heap_lock()
            try:
                SecretOwner()
            except MemoryError:
                failed = True
            finally:
                micropython.heap_unlock()
            self.assertTrue(failed)
        owner = SecretOwner()
        self.assertTrue(owner.valid())
        owner.destroy()

    def test_completion_and_exception(self):
        for fail in (False, True):
            values = []
            callbacks = []

            def work():
                values.append(secbytes(KEY))
                if fail:
                    raise ValueError("expected failure")
                yield None

            def finished(task, result):
                self.assert_invalid(values[0])
                callbacks.append(result)

            task = work()
            session, owner = self.root(task, finalizer=finished)
            self.step(task)
            if not fail:
                self.assertTrue(owner.valid())
                self.step(task)
            self.assertFalse(owner.valid())
            self.assertTrue(session.valid())
            self.assertEqual(len(callbacks), 1)

    def test_concurrent_sessions_and_cross_owner(self):
        values = []

        def work():
            values.append(secbytes(KEY))
            yield None
            secp256k1.sign(values[0], DIGEST)

        first, second = work(), work()
        session1, owner1 = self.root(first)
        session2, owner2 = self.root(second)
        self.step(first)
        self.step(second)
        _secret_owner_activate(owner2)
        self.assert_invalid(values[0])
        self.assertEqual(secp256k1.sign(values[1], DIGEST), secp256k1.sign(KEY, DIGEST))
        loop.close(first)
        self.assertFalse(owner1.valid())
        _secret_owner_activate(owner2)
        self.assertEqual(secp256k1.sign(values[1], DIGEST), secp256k1.sign(KEY, DIGEST))
        session1.destroy()
        self.assertTrue(session2.valid())
        self.assertTrue(owner2.valid())
        session2.destroy()
        self.assertFalse(owner2.valid())
        self.step(second)  # public teardown may resume, but secret use fails closed

    def test_child_inherits_and_does_not_revoke(self):
        values, children = [], []

        def child():
            values.append(secbytes(KEY))
            yield None

        def parent():
            children.append(child())
            loop.schedule(children[0])
            yield None
            values.append(secbytes(KEY))
            yield None

        task = parent()
        session, owner = self.root(task)
        self.step(task)
        self.step(children[0])
        self.step(children[0])
        self.assertTrue(owner.valid())
        self.step(task)
        loop.close(task)
        self.assertFalse(owner.valid())
        self.assertEqual(len(values), 2)
        _secret_owner_activate(session)
        for key in values:
            self.assert_invalid(key)

    def test_await_race_cancels_child_only(self):
        values, racers = [], []

        async def slow():
            values.append(secbytes(KEY))
            await loop.sleep(10000)

        async def fast():
            return 1

        async def parent():
            key = secbytes(KEY)
            values.append(key)
            racer = loop.race(slow(), fast())
            racers.append(racer)
            await racer
            self.assertEqual(secp256k1.sign(key, DIGEST), secp256k1.sign(KEY, DIGEST))
            await loop.sleep(10)

        task = parent()
        session, owner = self.root(task)
        self.step(task)
        self.step(racers[0].scheduled[0])
        self.step(racers[0].scheduled[1])
        self.assertTrue(owner.valid())
        self.step(task)
        self.assertFalse(owner.valid())
        self.assertTrue(session.valid())
        for value in values:
            self.assert_invalid(value)

    def test_nested_step_restores_owner(self):
        values = []

        def nested():
            values.append(secbytes(KEY))
            yield None

        other = nested()
        _, nested_owner = self.root(other)
        self.step(other)
        test = self

        class NestedStep(loop._RealSyscall):
            def handle(self, task):
                test.step(other)
                test.assertIs(loop.this_task, task)
                values.append(secbytes(KEY))  # must belong to the outer request

        def outer():
            yield NestedStep()

        task = outer()
        _, owner = self.root(task)
        self.step(task)
        self.assertFalse(nested_owner.valid())
        self.assertTrue(owner.valid())
        _secret_owner_activate(owner)
        self.assertEqual(secp256k1.sign(values[1], DIGEST), secp256k1.sign(KEY, DIGEST))
        self.step(task)
        self.assertFalse(owner.valid())

    def test_close_raises_and_clear_without_unwinding(self):
        values, unwound = [], []

        def work():
            try:
                values.append(secbytes(KEY))
                yield None
            finally:
                unwound.append(True)
                raise ValueError("close failed")

        task = work()
        session, owner = self.root(task)
        self.step(task)
        with self.assertRaises(ValueError):
            loop.close(task)
        self.assertFalse(owner.valid())
        self.assertEqual(unwound, [True])
        task = work()
        session2, owner2 = self.root(task)
        self.step(task)
        # Security teardown must not allocate or execute coroutine finalizers.
        micropython.heap_lock()
        try:
            loop.clear()
        finally:
            micropython.heap_unlock()
        self.assertFalse(owner2.valid())
        self.assertTrue(session.valid())
        self.assertTrue(session2.valid())
        self.assertEqual(unwound, [True])
        for key in values:
            self.assert_invalid(key)
        with self.assertRaises(ValueError):
            task.close()  # close only after proving clear did not unwind

    def test_retention_and_session_cascade(self):
        session = SecretOwner()
        request = SecretOwner(session)
        _secret_owner_activate(request)
        key = secbytes(KEY)
        node = bip32.from_seed(KEY, "secp256k1")
        retain_secret(key)
        retain_secret(node)
        request.destroy()
        other = SecretOwner(session)
        _secret_owner_activate(other)
        self.assertEqual(secp256k1.sign(key, DIGEST), secp256k1.sign(KEY, DIGEST))
        # A clone is the same sealed secret, so it shares the session lifetime
        # of the retained node: no secret outlives its owner.
        clone = node.clone()
        loop.clear()  # session entries survive, requests do not
        self.assertFalse(other.valid())
        _secret_owner_activate(session)
        self.assertEqual(secp256k1.sign(key, DIGEST), secp256k1.sign(KEY, DIGEST))
        self.assertEqual(clone.public_key(), node.public_key())
        micropython.heap_lock()
        try:
            session.destroy()
            session.destroy()
        finally:
            micropython.heap_unlock()
        self.assertFalse(session.valid())
        self.assert_invalid(key)
        with self.assertRaises(ValueError):
            clone.public_key()

    def test_session_cache_end_and_eviction(self):
        if utils.USE_THP:
            from storage.cache_thp import SessionThpCache

            cache = SessionThpCache()
        else:
            from storage import cache_codec

            cache_codec.clear_all()
            cache_codec.start_session()
            cache = cache_codec.get_active_session()
        session = cache.get_secret_owner()
        request = SecretOwner(session)
        _secret_owner_activate(request)
        key = secbytes(KEY)
        retain_secret(key)
        if utils.USE_THP:
            cache.clear()
        else:
            # Exercise real LRU reuse rather than destroying the owner directly.
            for _ in range(cache_codec._MAX_SESSIONS_COUNT):
                cache_codec.start_session()
        self.assertFalse(session.valid())
        self.assertFalse(request.valid())
        new_owner = cache.get_secret_owner()
        self.assertTrue(new_owner.valid())
        # The session cache deliberately renews the same preallocated holder.
        # The old request is a separate, already-revoked capability.
        self.assertIs(new_owner, session)
        request.destroy()
        self.assertTrue(new_owner.valid())
        cache.clear()
        self.assertFalse(new_owner.valid())
        self.assert_invalid(key)
        if not utils.USE_THP:
            cache_codec.clear_all()

    def test_native_vm_reset_hook(self):
        values = []

        def work():
            key = secbytes(KEY)
            retain_secret(key)
            values.append(key)
            yield None

        task = work()
        session, owner = self.root(task)
        self.step(task)
        # Same allocation-free C hook used before mp_init and mp_deinit.
        micropython.heap_lock()
        try:
            revoke_secrets()
        finally:
            micropython.heap_unlock()
        self.assertFalse(session.valid())
        self.assertFalse(owner.valid())
        self.assertTrue(_secret_task_enter(task))  # binding was forgotten by reset
        self.assert_invalid(values[0])
        replacement = SecretOwner()
        session.destroy()
        self.assertTrue(replacement.valid())

    def test_syscall_and_callback_failures(self):
        class FailingSyscall(loop._RealSyscall):
            def handle(self, task):
                raise MemoryError("syscall failed")

        def work():
            secbytes(KEY)
            yield FailingSyscall()

        task = work()
        session, owner = self.root(task)
        with self.assertRaises(MemoryError):
            self.step(task)
        self.assertFalse(owner.valid())
        self.assertTrue(session.valid())

        def completed():
            secbytes(KEY)
            yield None

        def callback(task, value):
            raise ValueError("callback failed")

        task = completed()
        session, owner = self.root(task, finalizer=callback)
        self.step(task)
        with self.assertRaises(ValueError):
            self.step(task)
        self.assertFalse(owner.valid())
        self.assertTrue(session.valid())

    def test_task_registration_failure_revokes_new_root(self):
        children = []

        def child():
            yield None

        def fill():
            for _ in range(63):
                task = child()
                children.append(task)
                loop.schedule(task)
            yield None

        first = fill()
        _, first_owner = self.root(first)
        self.step(first)  # 64 bindings, including the root
        session = SecretOwner()
        owner = SecretOwner(session)
        task = child()
        with self.assertRaises(MemoryError):
            loop.schedule(task, secret_owner=owner)
        self.assertFalse(owner.valid())
        self.assertTrue(session.valid())
        self.assertTrue(first_owner.valid())
        loop.clear()
        self.assertFalse(first_owner.valid())
        task.close()

    def test_cache_failure_revokes_before_allocating(self):
        from storage.cache_common import DataCache

        class Cache(DataCache):
            fields = (1,)

        cache = Cache()
        session = cache.get_secret_owner()
        request = SecretOwner(session)
        _secret_owner_activate(request)
        key = secbytes(KEY)
        micropython.heap_lock()
        try:
            try:
                cache.clear()
            except MemoryError:
                pass  # bytearray cache cleanup may allocate after vault revocation
        finally:
            micropython.heap_unlock()
        self.assertFalse(session.valid())
        self.assertFalse(request.valid())
        self.assert_invalid(key)

    def test_signing_failure_revokes_request(self):
        values = []

        def work():
            key = secbytes(b"\x00" * 32)
            values.append(key)
            secp256k1.sign(key, DIGEST)
            yield None

        task = work()
        session, owner = self.root(task)
        self.step(task)
        self.assertFalse(owner.valid())
        self.assertTrue(session.valid())
        self.assert_invalid(values[0])

    def test_many_values_keep_request(self):
        # There is no kernel pool to exhaust: a request may hold any number of
        # sealed values, and they die with the request.
        values = []

        def work():
            for _ in range(65):
                values.append(secbytes(KEY))
            yield None

        task = work()
        session, owner = self.root(task)
        self.step(task)
        self.assertTrue(owner.valid())
        _secret_owner_activate(owner)
        self.assertEqual(
            secp256k1.sign(values[64], DIGEST), secp256k1.sign(KEY, DIGEST)
        )
        owner.destroy()
        _secret_owner_activate(SecretOwner(session))
        for key in values:
            self.assert_invalid(key)


if __name__ == "__main__":
    unittest.main()
