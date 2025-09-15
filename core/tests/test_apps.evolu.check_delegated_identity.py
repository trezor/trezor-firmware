from common import *
from apps.evolu.common import compute_proof_sought_value


class TestCheckDelegatedIdentityKey(unittest.TestCase):
    def test_compute_proof_sought_value_sign_request(self):
        from trezor.utils import delegated_identity
        import trezorcrypto

        private_key = delegated_identity()

        sign_request_challenge: int = 1234
        sign_request_size: int = 10

        # Create a SHA256 hash object
        sha256 = trezorcrypto.sha256()

        # Update the hash with data
        sha256.update(b"EvoluSignRegistrationRequest")
        sha256.update(b"|")
        sha256.update(private_key)
        sha256.update(b"|")
        sha256.update(sign_request_challenge.to_bytes(16, "big"))
        sha256.update(b"|")
        sha256.update(sign_request_size.to_bytes(16, "big"))

        # Get the digest
        check_hash = sha256.digest()

        arguments = [
            sign_request_challenge.to_bytes(16, "big"),
            sign_request_size.to_bytes(16, "big"),
        ]
        self.assertEqual(
            compute_proof_sought_value(
                header=b"EvoluSignRegistrationRequest",
                arguments=arguments,
            ),
            check_hash,
        )

    def test_compute_proof_sought_value_get_node(self):
        from trezor.utils import delegated_identity
        import trezorcrypto

        private_key = delegated_identity()

        sha256 = trezorcrypto.sha256()
        sha256.update(b"EvoluGetNode")
        sha256.update(b"|")
        sha256.update(private_key)

        check_hash = sha256.digest()

        self.assertEqual(
            compute_proof_sought_value(header=b"EvoluGetNode", arguments=[]),
            check_hash,
        )

    def test_compute_proof_sought_value_false(self):
        from trezor.utils import delegated_identity
        import trezorcrypto

        private_key = delegated_identity()

        sha256 = trezorcrypto.sha256()
        sha256.update(b"EvoluGetNode")
        # sha256.update(b"|")           # omit this to get a different hash
        sha256.update(private_key)

        check_hash = sha256.digest()

        self.assertNotEqual(
            compute_proof_sought_value(header=b"EvoluGetNode", arguments=[]),
            check_hash,
        )

    def test_check_delegetad_identity_key(self):
        from apps.evolu.common import check_delegetad_identity_key
        from trezor.utils import delegated_identity
        import ubinascii

        if delegated_identity() != ubinascii.unhexlify(
            "0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20"
        ):
            return  # skip the test if the key is not the hardcoded one

        # Proof value for hardcoded private_key 0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20
        proposed_value = ubinascii.unhexlify(
            "1a11f06bc2e2e1e451862f2fa478edd698fbdf93bd9a9dc151edcbc38c9b9f37"
        )
        header = b"EvoluSignRegistrationRequest"
        sign_request_challenge: int = 1234
        sign_request_size: int = 10
        arguments = [
            sign_request_challenge.to_bytes(16, "big"),
            sign_request_size.to_bytes(16, "big"),
        ]

        self.assertEqual(
            check_delegetad_identity_key(proposed_value, header, arguments), True
        )


if __name__ == "__main__":
    unittest.main()
