# flake8: noqa: F403,F405
from common import *  # isort:skip
from trezor import utils

# make -C core test TESTOPTS=test_apps.evolu.check_evolu.py


@unittest.skipUnless(utils.USE_OPTIGA, "only needed with Optiga")
class TestCheckDelegatedIdentityKey(unittest.TestCase):

    def test_sign_registration_request(self):
        from trezorutils import delegated_identity
        from ubinascii import unhexlify

        from trezor.crypto.curve import nist256p1
        from trezor.crypto.hashlib import sha256
        from trezor.utils import HashWriter

        from apps.common.writers import write_compact_size
        from apps.evolu.common import check_delegated_identity_proof

        # sign_registration_request
        header = b"EvoluSignRegistrationRequest"
        sign_request_challenge: str = "1234"
        sign_request_size: int = 10
        arguments = [
            unhexlify(sign_request_challenge),
            sign_request_size.to_bytes(4, "big"),
        ]

        h = HashWriter(sha256())
        write_compact_size(h, len(header))
        h.extend(header)

        for arg in arguments:
            write_compact_size(h, len(arg))
            h.extend(arg)
        proof = nist256p1.sign(
            delegated_identity(),
            h.get_digest(),
        )

        self.assertEqual(check_delegated_identity_proof(proof, header, arguments), True)

    def test_sign_registration_request_invalid_size(self):
        from ubinascii import unhexlify

        from trezor.wire import DataError

        from apps.evolu.evolu_sign_registration_request import _check_data

        sign_request_challenge = unhexlify("1234")
        sign_request_size: int = 256**4 + 5  # invalid size

        with self.assertRaises(DataError):
            _check_data(sign_request_challenge, sign_request_size)

        sign_request_size: int = -1  # invalid size

        with self.assertRaises(DataError):
            _check_data(sign_request_challenge, sign_request_size)

    def test_sign_registration_request_invalid_challenge(self):
        from ubinascii import unhexlify

        from trezor.wire import DataError

        from apps.evolu.evolu_sign_registration_request import _check_data

        sign_request_challenge = unhexlify("")  # invalid length
        sign_request_size: int = 10

        with self.assertRaises(DataError):
            _check_data(sign_request_challenge, sign_request_size)

    def test_get_evolu_node(self):
        from trezorutils import delegated_identity

        from trezor.crypto.curve import nist256p1
        from trezor.crypto.hashlib import sha256
        from trezor.utils import HashWriter

        from apps.common.writers import write_compact_size
        from apps.evolu.common import check_delegated_identity_proof

        # get_node

        header = b"EvoluGetNode"

        h = HashWriter(sha256())
        write_compact_size(h, len(header))
        h.extend(header)

        proof = nist256p1.sign(
            delegated_identity(),
            h.get_digest(),
        )

        self.assertEqual(
            check_delegated_identity_proof(proof, header, arguments=[]), True
        )
        self.assertEqual(check_delegated_identity_proof(proof, header), True)


if __name__ == "__main__":
    unittest.main()
