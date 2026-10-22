# flake8: noqa: F403,F405
from common import *  # isort:skip

import struct
from trezorcrypto import (
    SecretOwner,
    _secret_owner_activate,
    _secret_task_enter,
    revoke_secrets,
    secbytes,
)

from trezor import config, loop
from trezor.crypto import bip32, bip39, hmac
from trezor.crypto.curve import ed25519, nist256p1
from trezor.crypto.hashlib import sha256

if not utils.BITCOIN_ONLY:
    from apps.common import cbor
    from apps.webauthn import common, fido2
    from apps.webauthn.credential import Fido2Credential, U2fCredential


@unittest.skipUnless(not utils.BITCOIN_ONLY, "fido2")
class TestSecureCredentials(unittest.TestCase):
    MNEMONIC = "all all all all all all all all all all all all"

    def setUp(self):
        config.init()
        config.wipe()
        self.assertTrue(config.unlock("", None))
        revoke_secrets()
        config.set(1, 2, self.MNEMONIC.encode())
        config.set(1, 0x0E, b"\x00")
        self.session = SecretOwner()
        self.request = SecretOwner(self.session)
        _secret_owner_activate(self.request)

    def tearDown(self):
        revoke_secrets()

    def next_request(self):
        self.request.destroy()
        self.request = SecretOwner(self.session)
        _secret_owner_activate(self.request)

    def test_u2f_handle_across_requests(self):
        credential = U2fCredential()
        credential.rp_id_hash = sha256(b"example.com").digest()
        credential.generate_key_handle()
        key = credential._private_key()
        self.assertIsInstance(key, secbytes)
        public = credential.public_key()
        signature = nist256p1.sign(key, b"\x42" * 32)
        self.assertTrue(nist256p1.verify(public, signature, b"\x42" * 32))
        self.next_request()
        with self.assertRaises(ValueError):
            nist256p1.publickey(key)
        self.assertEqual(credential.public_key(), public)
        restored = U2fCredential.from_key_handle(credential.id, credential.rp_id_hash)
        self.assertEqual(restored.public_key(), public)
        with self.assertRaises(ValueError):
            U2fCredential.from_key_handle(credential.id, b"\x00" * 32)
        with self.assertRaises(ValueError):
            U2fCredential.from_key_handle(
                credential.id[:-1] + bytes([credential.id[-1] ^ 1]),
                credential.rp_id_hash,
            )

    def test_legacy_big_endian_handle(self):
        credential = U2fCredential()
        credential.rp_id_hash = sha256(b"example.com").digest()
        credential.generate_key_handle()
        keypath = struct.pack(">8L", *struct.unpack("<8L", credential.id[:32]))
        tag = hmac.tag(
            hmac.SHA256, credential._private_key(), credential.rp_id_hash + keypath
        )
        restored = U2fCredential.from_key_handle(keypath + tag, credential.rp_id_hash)
        self.assertEqual(restored.public_key(), credential.public_key())

    def test_fido2_p256_derivation(self):
        credential = Fido2Credential()
        credential.id = bytes(range(32))
        private = credential._private_key()
        self.assertIsInstance(private, secbytes)
        expected = bip32.from_seed(bip39.seed(self.MNEMONIC, ""), "nist256p1")
        expected.derive_path(
            [0x80002726, 0x80010203, 0x90111213, 0x94151617, 0x98191A1B, 0x9C1D1E1F]
        )
        public = expected.public_key()
        self.assertEqual(nist256p1.publickey(private), public)
        self.next_request()
        self.assertEqual(nist256p1.publickey(credential._private_key()), public)

    def test_ed25519_large_self_attestation(self):
        credential = Fido2Credential()
        credential.id = bytes(range(256)) * 4
        credential.algorithm = common.COSE_ALG_EDDSA
        credential.curve = common.COSE_CURVE_ED25519
        credential.rp_id_hash = sha256(b"example.com").digest()
        credential.hmac_secret = True
        key = credential._private_key()
        self.assertIsInstance(key, secbytes)
        public = ed25519.publickey(key)
        self.assertEqual(
            cbor.decode(credential.public_key())[common.COSE_KEY_X], public
        )
        challenge = b"x" * 32
        response = cbor.decode(
            fido2._cbor_make_credential_sign(challenge, credential, False)
        )
        auth_data, attestation = response[2], response[3]
        self.assertTrue(len(auth_data + challenge) > 256)
        self.assertTrue(
            ed25519.verify(public, attestation["sig"], auth_data + challenge)
        )
        self.next_request()
        with self.assertRaises(ValueError):
            ed25519.publickey(key)
        self.assertEqual(ed25519.publickey(credential._private_key()), public)
        assertion = cbor.decode(
            fido2.cbor_get_assertion_sign(
                challenge, credential.rp_id_hash, credential, None, False, True, False
            )
        )
        self.assertTrue(ed25519.verify(public, assertion[3], assertion[2] + challenge))

    def test_command_owner_cleanup(self):
        original_dispatch, original_send = fido2._dispatch_cmd, fido2.send_cmd
        values = []

        def dispatch(req, manager):
            values.append(bip32.from_seed(b"seed", "nist256p1").private_key())
            if req == 1:
                raise ValueError("expected dispatch failure")
            return object()

        async def send(response, iface):
            await loop.sleep(10000)

        class Manager:
            iface = None

        fido2._dispatch_cmd, fido2.send_cmd = dispatch, send
        try:
            for failure in (0, 1, 2):
                owner = SecretOwner(self.session)
                task = fido2._dispatch_and_send(failure, Manager())
                loop.schedule(task, secret_owner=owner)
                loop._queue.discard(task)
                loop._step(task, None)
                if failure != 1:
                    self.assertTrue(owner.valid())
                    if failure == 0:
                        loop.close(task)
                    else:
                        loop._queue.discard(task)
                        loop._step(task, None)
                self.assertFalse(owner.valid())
                _secret_owner_activate(self.request)
                with self.assertRaises(ValueError):
                    nist256p1.publickey(values[-1])
        finally:
            fido2._dispatch_cmd, fido2.send_cmd = original_dispatch, original_send
            loop.clear()

    def test_dialog_owner_is_independent(self):
        class State:
            finished = False

            def timeout_ms(self):
                return 10000

        manager = fido2.DialogManager(None)
        original_owner = fido2.SecretOwner
        owners = []

        def owner_factory(parent):
            owner = original_owner(parent)
            owners.append(owner)
            return owner

        fido2.SecretOwner = owner_factory
        try:
            self.assertTrue(manager.set_state(State()))
            task = manager.workflow.task
            self.assertTrue(_secret_task_enter(task))
            key = bip32.from_seed(b"seed", "nist256p1").private_key()
            public = nist256p1.publickey(key)
            self.request.destroy()
            self.assertTrue(_secret_task_enter(task))
            self.assertEqual(nist256p1.publickey(key), public)
            manager.reset()
            self.assertFalse(owners[0].valid())
            _secret_task_enter(task)
            with self.assertRaises(ValueError):
                nist256p1.publickey(key)
        finally:
            fido2.SecretOwner = original_owner
            manager.reset()
            loop.clear()


if __name__ == "__main__":
    unittest.main()
