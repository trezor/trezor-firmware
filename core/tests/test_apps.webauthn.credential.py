from common import *
import storage
import storage.device
from apps.common import mnemonic
from apps.webauthn.credential import Fido2Credential, U2fCredential, NAME_MAX_LENGTH
from apps.webauthn.fido2 import distinguishable_cred_list
from trezor.crypto.curve import nist256p1
from trezor.crypto.hashlib import sha256


class TestCredential(unittest.TestCase):
    def test_fido2_credential_decode(self):
        mnemonic_secret = b"all all all all all all all all all all all all"
        mnemonic.get_secret = lambda: mnemonic_secret
        storage.device.is_initialized = lambda: True

        cred_id = (
            b"f1d0020013e65c865634ad8abddf7a66df56ae7d8c3afd356f76426801508b2e"
            b"579bcb3496fe6396a6002e3cd6d80f6359dfa9961e24c544bfc2f26acec1b8d8"
            b"78ba56727e1f6a7b5176c607552aea63a5abe5d826d69fab3063edfa0201d9a5"
            b"1013d69eddb2eff37acdd5963f"
        )

        rp_id = "example.com"
        rp_id_hash = sha256(rp_id).digest()

        user_id = (
            b"3082019330820138a0030201023082019330820138a003020102308201933082"
        )

        user_name = "johnpsmith@example.com"

        creation_time = 2

        public_key = (
            b"a501020326200121582051f0d4c307bc737c90ac605c6279f7d01e451798aa7b"
            b"74df550fdb43a7760c7c22582002b5107fef42094d00f52a9b1e90afb90e1b9d"
            b"ecbf15a6f13d4f882de857e2f4"
        )

        cred_random = (
            b"36a9b5d71c13ed54594474b54073af1fb03ea91cd056588909dae43ae2f35dbf"
        )

        # Load credential.
        cred = Fido2Credential.from_cred_id(unhexlify(cred_id), rp_id_hash)
        self.assertIsNotNone(cred)

        # Check credential data.
        self.assertEqual(hexlify(cred.id), cred_id)
        self.assertEqual(cred.rp_id, rp_id)
        self.assertEqual(cred.rp_id_hash, rp_id_hash)
        self.assertEqual(hexlify(cred.user_id), user_id)
        self.assertEqual(cred.user_name, user_name)
        self.assertEqual(cred.creation_time, creation_time)
        self.assertTrue(cred.hmac_secret)
        self.assertIsNone(cred.rp_name)
        self.assertIsNone(cred.user_display_name)

        # Check credential keys.
        self.assertEqual(hexlify(cred.hmac_secret_key()), cred_random)
        self.assertEqual(hexlify(cred.public_key()), public_key)

    def test_truncation(self):
        cred = Fido2Credential()
        cred.truncate_names()
        self.assertIsNone(cred.rp_name)
        self.assertIsNone(cred.user_name)
        self.assertIsNone(cred.user_display_name)

        cred.rp_name = "a" * (NAME_MAX_LENGTH - 2) + "\u0123"
        cred.user_name = "a" * (NAME_MAX_LENGTH - 1) + "\u0123"
        cred.user_display_name = "a" * NAME_MAX_LENGTH + "\u0123"
        cred.truncate_names()
        self.assertEqual(cred.rp_name, "a" * (NAME_MAX_LENGTH - 2) + "\u0123")
        self.assertEqual(cred.user_name, "a" * (NAME_MAX_LENGTH - 1))
        self.assertEqual(cred.user_display_name, "a" * NAME_MAX_LENGTH)

    def test_allow_list_processing(self):
        a1 = Fido2Credential()
        a1.user_id = b"user-a"
        a1.user_name = "user-a"
        a1.creation_time = 1

        a2 = Fido2Credential()
        a2.user_id = b"user-a"
        a2.user_display_name = "User A"
        a2.creation_time = 3

        a3 = Fido2Credential()
        a3.user_id = b"user-a"
        a3.user_name = "User A"
        a3.creation_time = 4

        b1 = Fido2Credential()
        b1.user_id = b"user-b"
        b1.creation_time = 2

        b2 = Fido2Credential()
        b2.user_id = b"user-b"
        b2.creation_time = 5

        b3 = Fido2Credential()
        b3.user_id = b"user-b"
        b3.creation_time = 5

        c1 = U2fCredential()

        c2 = U2fCredential()

        self.assertEqual(sorted(distinguishable_cred_list([a1, a2, a3, b1, b2, c1, c2])), [b2, a3, a1, c1])
        self.assertEqual(sorted(distinguishable_cred_list([c2, c1, b2, b1, a3, a2, a1])), [b2, a3, a1, c2])

        # Test input by creation time.
        self.assertEqual(sorted(distinguishable_cred_list([b2, a3, c1, a2, b1, a1, c2])), [b2, a3, a1, c1])
        self.assertEqual(sorted(distinguishable_cred_list([c2, a1, b1, a2, c1, a3, b2])), [b2, a3, a1, c2])

        # Test duplicities.
        self.assertEqual(sorted(distinguishable_cred_list([c1, a1, a1, c2, c1])), [a1, c1])
        self.assertEqual(sorted(distinguishable_cred_list([b2, b3])), [b2])
        self.assertEqual(sorted(distinguishable_cred_list([b3, b2])), [b3])


if __name__ == '__main__':
    unittest.main()
