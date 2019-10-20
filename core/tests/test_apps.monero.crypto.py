from common import *

if not utils.BITCOIN_ONLY:
    from apps.monero.xmr import crypto, monero
    from apps.monero.xmr.addresses import encode_addr
    from apps.monero.xmr.credentials import AccountCreds
    from apps.monero.xmr.networks import NetworkTypes, net_version


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestMoneroCrypto(unittest.TestCase):

    def test_encoding(self):
        point = unhexlify(
            b"2486224797d05cae3cba4be043be2db0df381f3f19cfa113f86ab38e3d8d2bd0"
        )
        self.assertEqual(point, crypto.encodepoint(crypto.decodepoint(point)))
        self.assertTrue(
            crypto.point_eq(
                crypto.decodepoint(point),
                crypto.decodepoint(crypto.encodepoint(crypto.decodepoint(point))),
            )
        )

    def test_scalarmult_base(self):
        scalar = crypto.decodeint(
            unhexlify(
                b"a0eea49140a3b036da30eacf64bd9d56ce3ef68ba82ef13571ec511edbcf8303"
            )
        )
        exp = unhexlify(
            b"16bb4a3c44e2ced511fc0d4cd86b13b3af21efc99fb0356199fac489f2544c09"
        )

        res = crypto.scalarmult_base(scalar)
        self.assertEqual(exp, crypto.encodepoint(res))
        self.assertTrue(crypto.point_eq(crypto.decodepoint(exp), res))

        scalar = crypto.decodeint(
            unhexlify(
                b"fd290dce39f781aebbdbd24584ed6d48bd300de19d9c3decfda0a6e2c6751d0f"
            )
        )
        exp = unhexlify(
            b"123daf90fc26f13c6529e6b49bfed498995ac383ef19c0db6771143f24ba8dd5"
        )

        res = crypto.scalarmult_base(scalar)
        self.assertEqual(exp, crypto.encodepoint(res))
        self.assertTrue(crypto.point_eq(crypto.decodepoint(exp), res))

    def test_scalarmult(self):
        priv = unhexlify(
            b"3482fb9735ef879fcae5ec7721b5d3646e155c4fb58d6cc11c732c9c9b76620a"
        )
        pub = unhexlify(
            b"2486224797d05cae3cba4be043be2db0df381f3f19cfa113f86ab38e3d8d2bd0"
        )
        exp = unhexlify(
            b"adcd1f5881f46f254900a03c654e71950a88a0236fa0a3a946c9b8daed6ef43d"
        )

        res = crypto.scalarmult(crypto.decodepoint(pub), crypto.decodeint(priv))
        self.assertEqual(exp, crypto.encodepoint(res))
        self.assertTrue(crypto.point_eq(crypto.decodepoint(exp), res))

    def test_cn_fast_hash(self):
        inp = unhexlify(
            b"259ef2aba8feb473cf39058a0fe30b9ff6d245b42b6826687ebd6b63128aff6405"
        )
        res = crypto.cn_fast_hash(inp)
        self.assertEqual(
            res,
            unhexlify(
                b"86db87b83fb1246efca5f3b0db09ce3fa4d605b0d10e6507cac253dd31a3ec16"
            ),
        )

    def test_hash_to_scalar(self):
        inp = unhexlify(
            b"259ef2aba8feb473cf39058a0fe30b9ff6d245b42b6826687ebd6b63128aff6405"
        )

        res = crypto.hash_to_scalar(inp)
        exp = crypto.decodeint(
            unhexlify(
                b"9907925b254e12162609fc0dfd0fef2aa4d605b0d10e6507cac253dd31a3ec06"
            )
        )
        self.assertTrue(crypto.sc_eq(res, exp))

    def test_hash_to_point(self):
        data = unhexlify(
            b"42f6835bf83114a1f5f6076fe79bdfa0bd67c74b88f127d54572d3910dd09201"
        )
        res = crypto.hash_to_point(data)
        res_p = crypto.encodepoint(res)
        self.assertEqual(
            res_p,
            unhexlify(
                b"54863a0464c008acc99cffb179bc6cf34eb1bbdf6c29f7a070a7c6376ae30ab5"
            ),
        )

    def test_derivation_to_scalar(self):
        derivation = unhexlify(
            b"e720a09f2e3a0bbf4e4ba7ad93653bb296885510121f806acb2a5f9168fafa01"
        )
        scalar = unhexlify(
            b"25d08763414c379aa9cf989cdcb3cadd36bd5193b500107d6bf5f921f18e470e"
        )

        sc_int = crypto.derivation_to_scalar(crypto.decodepoint(derivation), 0)
        self.assertEqual(scalar, crypto.encodeint(sc_int))

    def test_generate_key_derivation(self):
        key_pub = crypto.decodepoint(
            unhexlify(
                b"7739c95d3298e2f87362dba9e0e0b3980a692ae8e2f16796b0e382098cd6bd83"
            )
        )
        key_priv = crypto.decodeint(
            unhexlify(
                b"3482fb9735ef879fcae5ec7721b5d3646e155c4fb58d6cc11c732c9c9b76620a"
            )
        )
        deriv_exp = unhexlify(
            b"fa188a45a0e4daccc0e6d4f6f6858fd46392104be74183ec0047e7e9f4eaf739"
        )

        self.assertEqual(
            deriv_exp,
            crypto.encodepoint(crypto.generate_key_derivation(key_pub, key_priv)),
        )

    def test_h(self):
        H = unhexlify(
            b"8b655970153799af2aeadc9ff1add0ea6c7251d54154cfa92c173a0dd39c1f94"
        )
        self.assertEqual(crypto.encodepoint(crypto.xmr_H()), H)

    def test_sc_inversion(self):
        res = crypto.new_scalar()
        inp = crypto.decodeint(
            unhexlify(
                b"3482fb9735ef879fcae5ec7721b5d3646e155c4fb58d6cc11c732c9c9b76620a"
            )
        )

        crypto.sc_inv_into(res, inp)
        self.assertEqual(
            hexlify(crypto.encodeint(res)),
            b"bcf365a551e6358f3f281a6241d4a25eded60230b60a1d48c67b51a85e33d70e",
        )

    def test_wallet_addr(self):
        addr = encode_addr(
            net_version(),
            unhexlify(
                b"3bec484c5d7f0246af520aab550452b5b6013733feabebd681c4a60d457b7fc1"
            ),
            unhexlify(
                b"2d5918e31d3c003da3c778592c07b398ad6f961a67082a75fd49394d51e69bbe"
            ),
        )

        self.assertEqual(
            addr,
            b"43tpGG9PKbwCpjRvNLn1jwXPpnacw2uVUcszAtgmDiVcZK4VgHwjJT9BJz1WGF9eMxSYASp8yNMkuLjeQfWqJn3CNWdWfzV",
        )

        w = AccountCreds.new_wallet(
            crypto.decodeint(
                unhexlify(
                    b"4ce88c168e0f5f8d6524f712d5f8d7d83233b1e7a2a60b5aba5206cc0ea2bc08"
                )
            ),
            crypto.decodeint(
                unhexlify(
                    b"f2644a3dd97d43e87887e74d1691d52baa0614206ad1b0c239ff4aa3b501750a"
                )
            ),
            network_type=NetworkTypes.TESTNET,
        )
        self.assertEqual(
            w.address,
            b"9vacMKaj8JJV6MnwDzh2oNVdwTLJfTDyNRiB6NzV9TT7fqvzLivH2dB8Tv7VYR3ncn8vCb3KdNMJzQWrPAF1otYJ9cPKpkr",
        )

    def test_derive_subaddress_public_key(self):
        out_key = crypto.decodepoint(
            unhexlify(
                b"f4efc29da4ccd6bc6e81f52a6f47b2952966442a7efb49901cce06a7a3bef3e5"
            )
        )
        deriv = crypto.decodepoint(
            unhexlify(
                b"259ef2aba8feb473cf39058a0fe30b9ff6d245b42b6826687ebd6b63128aff64"
            )
        )
        res = crypto.encodepoint(monero.derive_subaddress_public_key(out_key, deriv, 5))
        self.assertEqual(
            res,
            unhexlify(
                b"5a10cca900ee47a7f412cd661b29f5ab356d6a1951884593bb170b5ec8b6f2e8"
            ),
        )

    def test_get_subaddress_secret_key(self):
        a = crypto.decodeint(
            unhexlify(
                b"4ce88c168e0f5f8d6524f712d5f8d7d83233b1e7a2a60b5aba5206cc0ea2bc08"
            )
        )
        m = monero.get_subaddress_secret_key(secret_key=a, major=0, minor=1)
        self.assertEqual(
            crypto.encodeint(m),
            unhexlify(
                b"b6ff4d689b95e3310efbf683850c075bcde46361923054e42ef30016b287ff0c"
            ),
        )

    def test_public_spend(self):
        derivation = unhexlify(
            b"e720a09f2e3a0bbf4e4ba7ad93653bb296885510121f806acb2a5f9168fafa01"
        )
        base = unhexlify(
            b"7d996b0f2db6dbb5f2a086211f2399a4a7479b2c911af307fdc3f7f61a88cb0e"
        )
        pkey_ex = unhexlify(
            b"0846cae7405077b6b7800f0b932c10a186448370b6db318f8c9e13f781dab546"
        )

        pkey_comp = crypto.derive_public_key(
            crypto.decodepoint(derivation), 0, crypto.decodepoint(base)
        )
        self.assertEqual(pkey_ex, crypto.encodepoint(pkey_comp))


if __name__ == "__main__":
    unittest.main()
