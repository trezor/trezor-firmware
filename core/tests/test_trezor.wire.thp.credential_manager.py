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
        DUMMY_KEY_1 = b"\x00\x00"
        DUMMY_KEY_2 = b"\xff\xff"
        HOST_NAME_1 = "host_name"
        HOST_NAME_2 = "different host_name"

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


if __name__ == "__main__":
    unittest.main()
