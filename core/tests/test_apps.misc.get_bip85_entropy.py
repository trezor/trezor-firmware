# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor import TR
from trezor.crypto import base58, bip32
from trezor.wire import DataError

from apps.misc.get_bip85_entropy import (
    _apply_application,
    _base64_encode,
    _base85_encode,
    _entropy_from_key,
    _validate_path,
)

# Master key from the BIP-85 test vectors:
# xprv9s21ZrQH143K2LBWUUQRFXhucrQqBpKdRRxNVq2zBqsx8HVqFk2uYo8kmbaLLHRdqtQpUm98uKfu3vca1LqdGhUtyoFnCNkfmXRyPXLjbKb
MASTER_XPRV = "xprv9s21ZrQH143K2LBWUUQRFXhucrQqBpKdRRxNVq2zBqsx8HVqFk2uYo8kmbaLLHRdqtQpUm98uKfu3vca1LqdGhUtyoFnCNkfmXRyPXLjbKb"


def master_node() -> bip32.HDNode:
    data = base58.decode_check(MASTER_XPRV)
    assert data[:4] == b"\x04\x88\xad\xe4"
    return bip32.HDNode(
        depth=0,
        fingerprint=0,
        child_num=0,
        chain_code=data[13:45],
        private_key=data[46:78],
        curve_name="secp256k1",
    )


def derive_entropy(path: list[int]) -> bytes:
    node = master_node()
    node.derive_path(path)
    return _entropy_from_key(node.private_key())


class TestBip85(unittest.TestCase):
    def test_entropy_vectors(self):
        # Test case 1 and 2 from BIP-85
        self.assertEqual(
            derive_entropy([H_(83696968), H_(0), H_(0)]),
            bytes.fromhex(
                "efecfbccffea313214232d29e71563d941229afb4338c21f9517c41aaa0d16f00b83d2a09ef747e7a64e8e2bd5a14869e693da66ce94ac2da570ab7ee48618f7"
            ),
        )
        self.assertEqual(
            derive_entropy([H_(83696968), H_(0), H_(1)]),
            bytes.fromhex(
                "70c6e3e8ebee8dc4c0dbba66076819bb8c09672527c4277ca8729532ad711872218f826919f6b67218adde99018a6df9095ab2b58d803b5b93ec9802085a690e"
            ),
        )

    def test_bip39(self):
        vectors = (
            (
                12,
                "6250b68daf746d12a24d58b4787a714b",
                "girl mad pet galaxy egg matter matrix prison refuse sense ordinary nose",
            ),
            (
                18,
                "938033ed8b12698449d4bbca3c853c66b293ea1b1ce9d9dc",
                "near account window bike charge season chef number sketch tomorrow excuse sniff circle vital hockey outdoor supply token",
            ),
            (
                24,
                "ae131e2312cdc61331542efe0d1077bac5ea803adf24b313a4f0e48e9c51f37f",
                "puppy ocean match cereal symbol another shed magic wrap hammer bulb intact gadget divorce twin tonight reason outdoor destroy simple truth cigar social volcano",
            ),
        )
        for words, entropy, mnemonic in vectors:
            path = [H_(83696968), H_(39), H_(0), H_(words), H_(0)]
            self.assertEqual(
                _validate_path(path), TR.bip85__app_bip39_template.format(words)
            )
            result_entropy, secret = _apply_application(path, derive_entropy(path))
            self.assertEqual(result_entropy, bytes.fromhex(entropy))
            self.assertEqual(secret, mnemonic)

    def test_wif(self):
        path = [H_(83696968), H_(2), H_(0)]
        self.assertEqual(_validate_path(path), TR.bip85__app_wif)
        entropy, secret = _apply_application(path, derive_entropy(path))
        self.assertEqual(
            entropy,
            bytes.fromhex(
                "7040bb53104f27367f317558e78a994ada7296c6fde36a364e5baf206e502bb1"
            ),
        )
        self.assertEqual(secret, "Kzyv4uF39d4Jrw2W7UryTHwZr1zQVNk4dAFyqE6BuMrMh1Za7uhp")

    def test_xprv(self):
        path = [H_(83696968), H_(32), H_(0)]
        self.assertEqual(_validate_path(path), TR.bip85__app_xprv)
        entropy, secret = _apply_application(path, derive_entropy(path))
        # BIP-85 lists the private key part (the second 32 bytes) as the derived key
        self.assertEqual(
            entropy[32:],
            bytes.fromhex(
                "ead0b33988a616cf6a497f1c169d9e92562604e38305ccd3fc96f2252c177682"
            ),
        )
        self.assertEqual(
            secret,
            "xprv9s21ZrQH143K2srSbCSg4m4kLvPMzcWydgmKEnMmoZUurYuBuYG46c6P71UGXMzmriLzCCBvKQWBUv3vPB3m1SATMhp3uEjXHJ42jFg7myX",
        )

    def test_hex(self):
        path = [H_(83696968), H_(128169), H_(64), H_(0)]
        self.assertEqual(_validate_path(path), TR.bip85__app_hex_template.format(64))
        entropy, secret = _apply_application(path, derive_entropy(path))
        self.assertEqual(
            entropy,
            bytes.fromhex(
                "492db4698cf3b73a5a24998aa3e9d7fa96275d85724a91e71aa2d645442f878555d078fd1f1f67e368976f04137b1f7a0d19232136ca50c44614af72b5582a5c"
            ),
        )
        self.assertIsNone(secret)

        path = [H_(83696968), H_(128169), H_(16), H_(0)]
        entropy, secret = _apply_application(path, derive_entropy(path))
        self.assertEqual(len(entropy), 16)

    def test_pwd_base64(self):
        path = [H_(83696968), H_(707764), H_(21), H_(0)]
        self.assertEqual(
            _validate_path(path), TR.bip85__app_pwd_base64_template.format(21)
        )
        entropy, secret = _apply_application(path, derive_entropy(path))
        self.assertEqual(
            entropy,
            bytes.fromhex(
                "74a2e87a9ba0cdd549bdd2f9ea880d554c6c355b08ed25088cfa88f3f1c4f74632b652fd4a8f5fda43074c6f6964a3753b08bb5210c8f5e75c07a4c2a20bf6e9"
            ),
        )
        self.assertEqual(secret, "dKLoepugzdVJvdL56ogNV")

    def test_pwd_base85(self):
        path = [H_(83696968), H_(707785), H_(12), H_(0)]
        self.assertEqual(
            _validate_path(path), TR.bip85__app_pwd_base85_template.format(12)
        )
        entropy, secret = _apply_application(path, derive_entropy(path))
        self.assertEqual(
            entropy,
            bytes.fromhex(
                "f7cfe56f63dca2490f65fcbf9ee63dcd85d18f751b6b5e1c1b8733af6459c904a75e82b4a22efff9b9e69de2144b293aa8714319a054b6cb55826a8e51425209"
            ),
        )
        self.assertEqual(secret, "_s`{TW89)i4`")

    def test_unknown_application(self):
        path = [H_(83696968), H_(89101), H_(6), H_(10), H_(0)]
        self.assertEqual(
            _validate_path(path), TR.bip85__app_unknown_template.format(89101)
        )
        raw = derive_entropy(path)
        entropy, secret = _apply_application(path, raw)
        self.assertEqual(entropy, raw)
        self.assertIsNone(secret)

    def test_invalid_paths(self):
        invalid = (
            [],
            [H_(83696968)],
            [83696968, H_(39), H_(0), H_(12), H_(0)],
            [H_(83696968), H_(39), H_(0), H_(12), 0],
            [H_(44), H_(0), H_(0)],
            [H_(83696968), H_(39), H_(0), H_(12)],
            [H_(83696968), H_(39), H_(0), H_(12), H_(0), H_(0)],
            [H_(83696968), H_(39), H_(0), H_(13), H_(0)],
            [H_(83696968), H_(39), H_(1), H_(12), H_(0)],
            [H_(83696968), H_(2), H_(0), H_(0)],
            [H_(83696968), H_(32)],
            [H_(83696968), H_(128169), H_(15), H_(0)],
            [H_(83696968), H_(128169), H_(65), H_(0)],
            [H_(83696968), H_(707764), H_(19), H_(0)],
            [H_(83696968), H_(707764), H_(87), H_(0)],
            [H_(83696968), H_(707785), H_(9), H_(0)],
            [H_(83696968), H_(707785), H_(81), H_(0)],
            [H_(83696968)] + [H_(0)] * 8,
        )
        for path in invalid:
            with self.assertRaises(DataError):
                _validate_path(path)

    def test_base64(self):
        self.assertEqual(_base64_encode(b""), "")
        self.assertEqual(_base64_encode(b"f"), "Zg==")
        self.assertEqual(_base64_encode(b"fo"), "Zm8=")
        self.assertEqual(_base64_encode(b"foo"), "Zm9v")
        self.assertEqual(_base64_encode(b"foob"), "Zm9vYg==")
        self.assertEqual(_base64_encode(b"fooba"), "Zm9vYmE=")
        self.assertEqual(_base64_encode(b"foobar"), "Zm9vYmFy")
        self.assertEqual(_base64_encode(bytes(range(256)))[:16], "AAECAwQFBgcICQoL")

    def test_base85(self):
        self.assertEqual(_base85_encode(b""), "")
        self.assertEqual(_base85_encode(b"\x00\x00\x00\x00"), "00000")
        self.assertEqual(_base85_encode(b"\xff\xff\xff\xff"), "|NsC0")
        self.assertEqual(_base85_encode(b"foobar12"), "W^Zp|VRA7t")


if __name__ == "__main__":
    unittest.main()
