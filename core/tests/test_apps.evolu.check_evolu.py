# flake8: noqa: F403,F405
from common import *  # isort:skip

# make -C core test TESTOPTS=test_apps.evolu.check_evolu.py


class TestCheckDelegatedIdentityKey(unittest.TestCase):

    def test_sign_registration_request(self):
        from ubinascii import unhexlify

        from trezor.crypto.curve import secp256k1
        from trezor.crypto.hashlib import sha256
        from trezor.utils import HashWriter
        from trezorutils import delegated_identity

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
        proposed_value = secp256k1.sign(
            delegated_identity(),
            h.get_digest(),
        )

        self.assertEqual(
            check_delegated_identity_proof(proposed_value, header, arguments), True
        )

    def test_get_evolu_node(self):
        from trezor.crypto.curve import secp256k1
        from trezor.crypto.hashlib import sha256
        from trezor.utils import HashWriter
        from trezorutils import delegated_identity

        from apps.common.writers import write_compact_size
        from apps.evolu.common import check_delegated_identity_proof

        # get_node

        header = b"EvoluGetNode"

        h = HashWriter(sha256())
        write_compact_size(h, len(header))
        h.extend(header)

        proposed_value = secp256k1.sign(
            delegated_identity(),
            h.get_digest(),
        )

        self.assertEqual(
            check_delegated_identity_proof(proposed_value, header, arguments=[]), True
        )
        self.assertEqual(check_delegated_identity_proof(proposed_value, header), True)


if __name__ == "__main__":
    unittest.main()
