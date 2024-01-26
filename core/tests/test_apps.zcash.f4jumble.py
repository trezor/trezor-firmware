from common import *  # isort:skip

from apps.zcash.f4jumble import f4jumble, f4unjumble


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestZcashF4jumble(unittest.TestCase):
    def test_f4jumble(self):
        # source: https://github.com/zcash/librustzcash/blob/main/components/f4jumble/src/test_vectors.rs
        TEST_VECTORS = [
            {
                "jumbled": unhexlify(
                    "0304d029141b995da5387c125970673504d6c764d91ea6c082123770c7139ccd88ee27368cd0c0921a0444c8e5858d22"
                ),
                "normal": unhexlify(
                    "5d7a8f739a2d9e945b0ce152a8049e294c4d6e66b164939daffa2ef6ee6921481cdd86b3cc4318d9614fc820905d042b"
                ),
            },
            {
                "jumbled": unhexlify(
                    "5271fa3321f3adbcfb075196883d542b438ec6339176537daf859841fe6a56222bff76d1662b5509a9e1079e446eeedd2e683c31aae3ee1851d7954328526be1"
                ),
                "normal": unhexlify(
                    "b1ef9ca3f24988c7b3534201cfb1cd8dbf69b8250c18ef41294ca97993db546c1fe01f7e9c8e36d6a5e29d4e30a73594bf5098421c69378af1e40f64e125946f"
                ),
            },
            {
                "jumbled": unhexlify(
                    "498cf1b1ba6f4577effe64151d67469adc30acc325e326207e7d78487085b4162669f82f02f9774c0cc26ae6e1a76f1e266c6a9a8a2f4ffe8d2d676b1ed71cc47195a3f19208998f7d8cdfc0b74d2a96364d733a62b4273c77d9828aa1fa061588a7c4c88dd3d3dde02239557acfaad35c55854f4541e1a1b3bc8c17076e7316"
                ),
                "normal": unhexlify(
                    "62c2fa7b2fecbcb64b6968912a6381ce3dc166d56a1d62f5a8d7551db5fd9313e8c7203d996af7d477083756d59af80d06a745f44ab023752cb5b406ed8985e18130ab33362697b0e4e4c763ccb8f676495c222f7fba1e31defa3d5a57efc2e1e9b01a035587d5fb1a38e01d94903d3c3e0ad3360c1d3710acd20b183e31d49f"
                ),
            },
            {
                "jumbled": unhexlify(
                    "7508a3a146714f229db91b543e240633ed57853f6451c9db6d64c6e86af1b88b28704f608582c53c51ce7d5b8548827a971d2b98d41b7f6258655902440cd66ee11e84dbfac7d2a43696fd0468810a3d9637c3fa58e7d2d341ef250fa09b9fb71a78a41d389370138a55ea58fcde779d714a04e0d30e61dc2d8be0da61cd684509"
                ),
                "normal": unhexlify(
                    "25c9a138f49b1a537edcf04be34a9851a7af9db6990ed83dd64af3597c04323ea51b0052ad8084a8b9da948d320dadd64f5431e61ddf658d24ae67c22c8d1309131fc00fe7f235734276d38d47f1e191e00c7a1d48af046827591e9733a97fa6b679f3dc601d008285edcbdae69ce8fc1be4aac00ff2711ebd931de518856878f7"
                ),
            },
            {
                "jumbled": unhexlify(
                    "5139912fe8b95492c12731995a0f4478dbeb81ec36653a21bc80d673f3c6a0feef70b6c566f9d34bb726c098648382d105afb19b2b8486b73cbd47a17a0d2d1fd593b14bb9826c5d114b850c6f0cf3083a6f61e38e42713a37ef7997ebd2b376c8a410d797b3932e5a6e39e726b2894ce79604b4ae3c00acaea3be2c1dfe697fa644755102cf9ad78794d0594585494fe38ab56fa6ef3271a68a33481015adf3944c115311421a7dc3ce73ef2abf47e18a6aca7f9dd25a85ce8dbd6f1ad89c8d"
                ),
                "normal": unhexlify(
                    "3476f21a482ec9378365c8f7393c94e2885315eb4671098b79535e790fe53e29fef2b3766697ac32b4f473f468a008e72389fc03880d780cb07fcfaabe3f1a84b27db59a4a153d882d2b2103596555ed9494c6ac893c49723833ec8926c1039586a7afcf4a0d9c731e985d99589c8bb838e8aaf745533ed9e8ae3a1cd074a51a20da8aba18d1dbebbc862ded42435e92476930d069896cff30eb414f727b89e001afa2fb8dc3436d75a4a6f26572504b192232ecb9f0c02411e52596bc5e9045"
                ),
            },
        ]

        for tv in TEST_VECTORS:
            message = memoryview(bytearray(tv["normal"]))
            f4jumble(message)
            self.assertEqual(bytes(message), tv["jumbled"])
            f4unjumble(message)
            self.assertEqual(bytes(message), tv["normal"])


if __name__ == "__main__":
    unittest.main()
