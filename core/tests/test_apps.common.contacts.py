# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor import wire
from trezor.crypto.curve import bip340

from apps.common import contacts

# Generated with @noble/curves schnorr + @noble/hashes sha256, independent of
# this implementation. Identity key = NIP-06 "leader monkey ..." at
# m/44'/1237'/0'/0/0.
PRIVKEY = bytes.fromhex(
    "7f7ff03d123792d6ac594bfa67bf6d0c0ab55b6b1fdb6249303fe861f1ccba9a"
)
PUBKEY = bytes.fromhex(
    "17162c921dc4d2518f9a101db33695df1afb56ab82f5ff3e5da6eec3ca5cd917"
)
NPUB = "npub1zutzeysacnf9rru6zqwmxd54mud0k44tst6l70ja5mhv8jjumytsd2x7nu"

VECTORS = (
    (
        0,
        "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
        "2dee871b3a47ded4249fd1b6cb18f399934f26df5236f225c2f4939c034be3aa",
        "03bb2571b492199ad2394ca3585e26e77c66fa7a6d93da5222c7c97a868f702269bb360c7dc097976d4495766a7ba9e8315d46ec99f45893ed8948b21cca2fe3",
    ),
    (
        1,
        "tb1qkvwu9g3k2pdxewfqr7syz89r3gj557l3uuf9r9",
        "c37b0ddc44f65de526f122c845e34de912783c32f887c44b0fd6482091bfb049",
        "b5b9f02efab327ccdc7a107f1b5d6d52800c6da7b01088f10f1f31793f8262761b2a102605b420cb01359d6ebd50a7383f20d7ccd136566f68f00d1271818674",
    ),
    (
        1,
        "mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q",
        "0db76d01fadc3830548bc78e6256397eb3c7e9da19b879d732c213dc1c503cfd",
        "93bd04015f82b5b71835e6faef74cd2216019ee2ddd0f02c45465673e9f51f99f9328a1c1d2378aaadfd27a80e4049442f48747c4c1432bb02773616752d76a4",
    ),
)


class TestContacts(unittest.TestCase):
    def test_digest(self):
        for slip44, address, digest, _ in VECTORS:
            self.assertEqual(
                contacts.attestation_digest(slip44, address), bytes.fromhex(digest)
            )

    def test_digest_binds_coin(self):
        _, address, digest, _ = VECTORS[1]
        self.assertNotEqual(
            contacts.attestation_digest(0, address), bytes.fromhex(digest)
        )

    def test_verify_vectors(self):
        for slip44, address, _, signature in VECTORS:
            signature = bytes.fromhex(signature)
            self.assertTrue(
                contacts.verify_attestation(PUBKEY, signature, slip44, address)
            )
            # other coin, other address, other key
            self.assertFalse(
                contacts.verify_attestation(PUBKEY, signature, slip44 ^ 1, address)
            )
            self.assertFalse(
                contacts.verify_attestation(
                    PUBKEY, signature, slip44, address[:-1] + "x"
                )
            )
            self.assertFalse(
                contacts.verify_attestation(
                    bip340.publickey(bip340.generate_secret()),
                    signature,
                    slip44,
                    address,
                )
            )

    def test_verify_malformed(self):
        slip44, address, _, signature = VECTORS[0]
        signature = bytes.fromhex(signature)
        self.assertFalse(
            contacts.verify_attestation(PUBKEY[:31], signature, slip44, address)
        )
        self.assertFalse(
            contacts.verify_attestation(PUBKEY, signature[:63], slip44, address)
        )
        self.assertFalse(
            contacts.verify_attestation(PUBKEY, signature, slip44, address + ":")
        )

    def test_sign_roundtrip(self):
        # bip340.sign uses fresh randomness, so compare by verification
        for slip44, address, digest, _ in VECTORS:
            signature = bip340.sign(PRIVKEY, bytes.fromhex(digest))
            self.assertTrue(
                contacts.verify_attestation(PUBKEY, signature, slip44, address)
            )

    def test_pubkey(self):
        self.assertEqual(bip340.publickey(PRIVKEY), PUBKEY)

    def test_npub(self):
        self.assertEqual(contacts.encode_npub(PUBKEY), NPUB)
        # NIP-19 example
        self.assertEqual(
            contacts.encode_npub(
                bytes.fromhex(
                    "3bf0c63fcb93463407af97a5e5ee64fa883d107ef9e558472c4eb9aaaefa459d"
                )
            ),
            "npub180cvv07tjdrrgpa0j7j7tmnyl2yr6yr7l8j4s3evf6u64th6gkwsyjh6w6",
        )
        with self.assertRaises(wire.DataError):
            contacts.encode_npub(PUBKEY[:31])

    def test_address_charset(self):
        for address in (
            "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
            "1BoatSLRHtKNngkdXEeobR76b53LETtpyT",
            "a",
            "Z" * 90,
        ):
            self.assertTrue(contacts.is_attestable_address(address))
        for address in (
            "",
            "Z" * 91,
            "bitcoincash:qr95sy3j9xwd2ap32xkykttr4cvcu7as4y0qverfuy",
            "bc1q ar0s",
            "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq\n",
            "bc1qčar0s",
        ):
            self.assertFalse(contacts.is_attestable_address(address))

    def test_attestable_path(self):
        for path in (
            [H_(84), H_(0), H_(0), 0, 0],
            [H_(44), H_(1), H_(5), 0, 999],
            [H_(86), H_(0), H_(0), 0, 7],
        ):
            self.assertTrue(contacts.is_attestable_path(path))
        for path in (
            [H_(84), H_(0), H_(0), 1, 0],  # change chain
            [H_(84), H_(0), H_(0), 0, 1000],  # index too high
            [H_(84), H_(0), H_(0), 0, H_(0)],  # hardened index
            [H_(84), H_(0), H_(0), 0],  # too short
            [H_(10025), H_(0), H_(0), H_(1), 0, 0],  # SLIP-25 coinjoin
            [H_(49), 0, 0, 0, 0],  # unhardened account (Casa)
        ):
            self.assertFalse(contacts.is_attestable_path(path))


if __name__ == "__main__":
    unittest.main()
