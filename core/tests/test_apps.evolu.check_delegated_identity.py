# flake8: noqa: F403,F405
from common import *  # isort:skip
from apps.evolu.common import compute_proof_value


class TestCheckDelegatedIdentityKey(unittest.TestCase):

    def test_compute_proof_value_sign_request(self):
        from trezor.crypto import hmac
        from trezor.utils import delegated_identity

        private_key = delegated_identity()

        sign_request_challenge: int = 1234
        sign_request_size: int = 10

        message = (
            b"EvoluSignRegistrationRequest"
            + b"\x00"
            + sign_request_challenge.to_bytes(16, "big")
            + b"\x00"
            + sign_request_size.to_bytes(16, "big")
        )
        check_hash = hmac(hmac.SHA256, private_key, message).digest()

        arguments = [
            sign_request_challenge.to_bytes(16, "big"),
            sign_request_size.to_bytes(16, "big"),
        ]
        self.assertEqual(
            compute_proof_value(
                header=b"EvoluSignRegistrationRequest",
                arguments=arguments,
            ),
            check_hash,
        )

    def test_compute_proof_value_get_node(self):
        from trezor.crypto import hmac
        from trezor.utils import delegated_identity

        private_key = delegated_identity()

        check_hash = hmac(hmac.SHA256, private_key, b"EvoluGetNode").digest()

        self.assertEqual(
            compute_proof_value(header=b"EvoluGetNode", arguments=[]),
            check_hash,
        )

    def test_compute_proof_value_false(self):
        from trezor.crypto import hmac
        from trezor.utils import delegated_identity

        private_key = delegated_identity()

        # introduce an error in the private_key
        private_key = bytearray(private_key)
        private_key[0] = 0x00 if private_key[0] != 0x00 else 0x01
        private_key = bytes(private_key)

        check_hash = hmac(hmac.SHA256, private_key, b"EvoluGetNode").digest()

        self.assertNotEqual(
            compute_proof_value(header=b"EvoluGetNode", arguments=[]),
            check_hash,
        )

    def test_check_delegated_identity_key_hardcoded(self):
        import ubinascii

        from trezor.utils import delegated_identity

        from apps.evolu.common import check_delegated_identity_key

        if delegated_identity() != ubinascii.unhexlify(
            "0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20"
        ):
            return  # skip the test if the key is not the hardcoded one

        # Proof values for hardcoded private_key 0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20
        # sign_registration_request
        proposed_value = ubinascii.unhexlify(
            "b952e499e907e5b370071bdaac28b7cfd5e42564fcbf03b2ec1cc62c444ba077"
        )
        header = b"EvoluSignRegistrationRequest"
        sign_request_challenge: int = 1234
        sign_request_size: int = 10
        arguments = [
            sign_request_challenge.to_bytes(16, "big"),
            sign_request_size.to_bytes(16, "big"),
        ]
        self.assertEqual(
            check_delegated_identity_key(proposed_value, header, arguments), True
        )

        # get_node
        proposed_value = ubinascii.unhexlify(
            "ea6b4912b51ef382a65fcd9aff0224ee3a84fc70794979019bf4f62b3212874d"
        )
        header = b"EvoluGetNode"
        self.assertEqual(check_delegated_identity_key(proposed_value, header), True)


if __name__ == "__main__":
    unittest.main()
