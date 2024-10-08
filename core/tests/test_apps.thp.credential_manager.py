from common import *
from trezor import config, utils
from trezor import log

if utils.USE_THP:
    from apps.thp import credential_manager
    from trezor.messages import ThpCredentialMetadata

    def _issue_credential(host_name: str, host_static_pubkey: bytes) -> bytes:
        metadata = ThpCredentialMetadata(host_name=host_name)
        return credential_manager.issue_credential(host_static_pubkey, metadata)

    def _dummy_log(name: str, msg: str, *args):
        pass

    log.debug = _dummy_log
    DUMMY_KEY_1 = b"\x00\x00"
    DUMMY_KEY_2 = b"\xff\xff"
    HOST_NAME_1 = "host_name"
    HOST_NAME_2 = "different host_name"


@unittest.skipUnless(utils.USE_THP, "only needed for THP")
class TestTrezorHostProtocolCredentialManager(unittest.TestCase):
    def setUp(self):
        config.init()
        config.wipe()

    def test_derive_cred_auth_key(self):
        key1 = credential_manager.derive_cred_auth_key()
        key2 = credential_manager.derive_cred_auth_key()
        self.assertEqual(len(key1), 32)
        self.assertEqual(key1, key2)

    def test_invalidate_cred_auth_key(self):
        key1 = credential_manager.derive_cred_auth_key()
        credential_manager.invalidate_cred_auth_key()
        key2 = credential_manager.derive_cred_auth_key()
        self.assertNotEqual(key1, key2)

    def test_credentials(self):

        cred_1 = _issue_credential(HOST_NAME_1, DUMMY_KEY_1)
        cred_2 = _issue_credential(HOST_NAME_1, DUMMY_KEY_1)
        self.assertEqual(cred_1, cred_2)

        cred_3 = _issue_credential(HOST_NAME_2, DUMMY_KEY_1)
        self.assertNotEqual(cred_1, cred_3)

        self.assertTrue(credential_manager.validate_credential(cred_1, DUMMY_KEY_1))
        self.assertTrue(credential_manager.validate_credential(cred_3, DUMMY_KEY_1))
        self.assertFalse(credential_manager.validate_credential(cred_1, DUMMY_KEY_2))

        credential_manager.invalidate_cred_auth_key()
        cred_4 = _issue_credential(HOST_NAME_1, DUMMY_KEY_1)
        self.assertNotEqual(cred_1, cred_4)
        self.assertFalse(credential_manager.validate_credential(cred_1, DUMMY_KEY_1))
        self.assertFalse(credential_manager.validate_credential(cred_3, DUMMY_KEY_1))
        self.assertTrue(credential_manager.validate_credential(cred_4, DUMMY_KEY_1))

    def test_protobuf_encoding(self):
        """
        If the protobuf encoding of credentials changes in the future, this
        test should be able to catch it.

        When the test fails, it might be necessary to create custom parser
        of credentials to ensure that credentials remain valid after FW update.
        """
        expected = b"\x0a\x0b\x0a\x09\x68\x6f\x73\x74\x5f\x6e\x61\x6d\x65\x12\x20\xf4\x44\x86\x2d\x00\x23\x1d\x02\xf3\x20\xbb\x58\xed\x13\x8f\xc6\x84\x9b\x6b\x73\x7a\x33\x25\xc4\x71\x79\x3b\x45\x15\xe4\x76\x67"

        # Use hard-coded bytes as a "credential auth key" when issuing a credential
        credential_manager.derive_cred_auth_key = lambda: b"\xBE\xEF"

        credential = _issue_credential(HOST_NAME_1, DUMMY_KEY_1)
        self.assertEqual(credential, expected)


if __name__ == "__main__":
    unittest.main()
