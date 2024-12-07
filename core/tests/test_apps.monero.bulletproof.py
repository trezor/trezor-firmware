# flake8: noqa: F403,F405
from common import *  # isort:skip

if not utils.BITCOIN_ONLY:
    from apps.monero.xmr import bulletproof as bp
    from apps.monero.xmr import crypto
    from apps.monero.xmr.serialize_messages.tx_rsig_bulletproof import BulletproofPlus


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestMoneroBulletproof(unittest.TestCase):
    def test_square_multiply(self):
        for x in [2, 3, 16, 17, 31, 32]:
            ss = crypto.random_scalar()
            s1 = crypto.sc_copy(None, ss)
            s2 = crypto.sc_copy(None, ss)
            for _ in range(1, x):
                crypto.sc_mul_into(s1, s1, ss)

            bp._sc_square_mult(s2, ss, x)
            self.assertEqual(
                crypto.encodeint_into(None, s1), crypto.encodeint_into(None, s2)
            )

    def test_dvct_skips(self):
        z_sq = unhexlify(
            b"e0408b528e9d35ccb8386b87f39b85c724740644f4db412483a8852cdb3ceb00"
        )
        d_vct0 = bp.VctD(64, 8, z_sq, raw=True)
        d_vct1 = bp.VctD(64, 8, z_sq, raw=True)
        tmp = crypto.Scalar()

        # Linear scan vs jump
        for i in range(65):
            tmp = d_vct0[i]
        self.assertEqual(
            crypto.encodeint_into(None, tmp), crypto.encodeint_into(None, d_vct1[64])
        )

        # Jumping around
        _ = d_vct0[128]
        self.assertEqual(
            crypto.encodeint_into(None, d_vct0[64]),
            crypto.encodeint_into(None, d_vct1[64]),
        )

        # Sync on the same jump
        self.assertEqual(
            crypto.encodeint_into(None, d_vct0[65]),
            crypto.encodeint_into(None, d_vct1[65]),
        )
        self.assertEqual(
            crypto.encodeint_into(None, d_vct0[65]),
            crypto.encodeint_into(None, d_vct1[65]),
        )

        # Jump vs linear again, move_one vs move_more
        for i in range(1, 10):
            tmp = d_vct0[65 + i]
        self.assertEqual(
            crypto.encodeint_into(None, tmp), crypto.encodeint_into(None, d_vct1[74])
        )

        _ = d_vct0[85]
        _ = d_vct1[89]  # different jump sizes, internal state management test
        self.assertEqual(
            crypto.encodeint_into(None, d_vct0[95]),
            crypto.encodeint_into(None, d_vct1[95]),
        )

        _ = d_vct0[319]  # move_one mults by z_sq then; enforce z component updates
        self.assertEqual(
            crypto.encodeint_into(None, d_vct0[320]),
            crypto.encodeint_into(None, d_vct1[320]),
        )

        tmp = crypto.sc_copy(None, d_vct0[64])  # another jump back and forth
        _ = d_vct0[127]
        self.assertEqual(
            crypto.encodeint_into(None, d_vct0[64]), crypto.encodeint_into(None, tmp)
        )

        _ = d_vct0[0]
        _ = d_vct1[0]
        _ = d_vct0[64]
        self.assertEqual(
            crypto.encodeint_into(None, d_vct0[5]),
            crypto.encodeint_into(None, d_vct1[5]),
        )

    def test_pow_back_skips(self):
        MN = 128
        y = unhexlify(
            "60421950bee0aab949e63336db1eb9532dba6b4599c5cd9fb1dbde909114100e"
        )
        y_sc = crypto.decodeint_into(None, y)
        yinv = bp._invert(None, y)

        y_to_MN_1 = bp._sc_square_mult(None, y_sc, MN - 1)
        ymax = crypto.sc_mul_into(None, y_to_MN_1, y_sc)  ## y**MN
        ymax2 = bp._sc_square_mult(None, y_sc, MN)
        self.assertEqual(
            crypto.encodeint_into(None, ymax), crypto.encodeint_into(None, ymax2)
        )

        size = MN + 1
        ypow_back = bp.KeyVPowersBackwards(size, y, x_inv=yinv, x_max=ymax, raw=True)
        self.assertEqual(
            crypto.encodeint_into(None, ymax),
            crypto.encodeint_into(None, ypow_back[MN]),
        )

        for i in range(10):
            _ = ypow_back[MN - i]

        self.assertEqual(
            crypto.encodeint_into(None, ypow_back[MN - 9]),
            crypto.encodeint_into(None, bp._sc_square_mult(None, y_sc, MN - 9)),
        )
        self.assertEqual(
            crypto.encodeint_into(None, ypow_back[MN - 19]),
            crypto.encodeint_into(None, bp._sc_square_mult(None, y_sc, MN - 19)),
        )
        self.assertEqual(
            crypto.encodeint_into(None, ypow_back[MN - 65]),
            crypto.encodeint_into(None, bp._sc_square_mult(None, y_sc, MN - 65)),
        )
        self.assertEqual(
            crypto.encodeint_into(None, ypow_back[MN - 14]),
            crypto.encodeint_into(None, bp._sc_square_mult(None, y_sc, MN - 14)),
        )

        tmp = crypto.sc_copy(None, ypow_back[MN - 64])  # another jump back and forth
        _ = ypow_back[MN - 127]
        self.assertEqual(
            crypto.encodeint_into(None, ypow_back[MN - 64]),
            crypto.encodeint_into(None, tmp),
        )
        self.assertEqual(
            crypto.encodeint_into(None, ypow_back[MN - 64]),
            crypto.encodeint_into(None, bp._sc_square_mult(None, y_sc, MN - 64)),
        )

    def test_bpp_bprime(self):
        N, M = 64, 4
        MN = N * M
        y = unhexlify(
            b"60421950bee0aab949e63336db1eb9532dba6b4599c5cd9fb1dbde909114100e"
        )
        z = unhexlify(
            b"e0408b528e9d35ccb8386b87f39b85c724740644f4db412483a8852cdb3ceb00"
        )
        zc = crypto.decodeint_into(None, z)
        z_sq = bp._sc_mul(None, z, z)
        sv = [1234, 8789, 4455, 6697]
        sv = [crypto.encodeint_into(None, crypto.Scalar(x)) for x in sv]

        num_inp = len(sv)
        sc_zero = crypto.decodeint_into_noreduce(None, bp._ZERO)
        sc_mone = crypto.decodeint_into_noreduce(None, bp._MINUS_ONE)

        def e_xL(idx, d=None):
            j, i = idx // bp._BP_N, idx % bp._BP_N
            r = None
            if j >= num_inp:
                r = sc_mone
            elif sv[j][i // 8] & (1 << i % 8):
                r = sc_zero
            else:
                r = sc_mone
            if d:
                return crypto.sc_copy(d, r)
            return r

        aR = bp.KeyVEval(MN, lambda i, d: e_xL(i, d), raw=True)
        d_vct = bp.VctD(N, M, z_sq, raw=True)
        ypow_back = bp.KeyVPowersBackwards(MN + 1, y, raw=True)
        aR1_sc1 = crypto.Scalar()

        def aR1_fnc(i, d):
            crypto.sc_add_into(aR1_sc1, aR.to(i), zc)
            crypto.sc_muladd_into(aR1_sc1, d_vct[i], ypow_back[MN - i], aR1_sc1)
            return crypto.encodeint_into(d, aR1_sc1)

        bprime = bp.KeyVEval(MN, aR1_fnc, raw=False)  # aR1
        b64 = bp._copy_key(None, bprime.to(64))
        b65 = bp._copy_key(None, bprime.to(65))
        b128 = bp._copy_key(None, bprime.to(128))
        b65_2 = bp._copy_key(None, bprime.to(65))
        b64_2 = bp._copy_key(None, bprime.to(64))
        _ = bprime[89]
        b128_2 = bp._copy_key(None, bprime.to(128))

        self.assertEqual(b64, b64_2)
        self.assertEqual(b65, b65_2)
        self.assertEqual(b128, b128_2)

    # fmt: off
    def bproof_plus_2(self):
        return BulletproofPlus(
            V=[
                unhexlify(b"e0dae61095ac728a15d4d9754f1f9f956c22d4fa2deee2c0ff1def031b083e02"),
                unhexlify(b"5b424ecb1f8ea02351d324296a34a0608ecc104610feaad06e6002f61992bfe1"),
            ],
            A=unhexlify(b"6ae6f16a6b01cf494fb2cf368573365293f76c624cfc11152d648479238e9319"),
            A1=unhexlify(b"33ad318a44df6f14a945e6d051911ab9a24841457d15d62bd1436fb3edc8a193"),
            B=unhexlify(b"5f56531cb8e78dbb3450f1d599a6d4c7f5e4c04ee3e7015643c19a528bcbb109"),

            r1=unhexlify(b"40ad8a9c6b3bdd95c7fb8605e50135050e64f1ce29d1c4b37b1271e658354500"),
            s1=unhexlify(b"aed959c770499134aaa7e099f566dac56ee12959d797b62a3d8d1037b790b806"),
            d1=unhexlify(b"395a1e8d3df8e90e716fdeaa493090782c8db922337d09a36b50c1f02cd8e100"),

            L=[unhexlify(b"ed2d768bb9c8b5a9fa24c90b5831d3cceb3e78cef45eba90e52f89a2b3c859d2"),
               unhexlify(b"7f25cc8e211783e9c1b80dd13ee286943da0ec07bd33291536639432758f6927"),
               unhexlify(b"7bae3d31f4e2a6d78d74d2bcb6d0656e4222161423d635f7ce08805e96cec83e"),
               unhexlify(b"c87f949f70cf569c4baa332612305733fd19a2262490c55ec88c16a68d7b5e7d"),
               unhexlify(b"34d06caf0d02129ebcc8bf318da8f6a0ddfaf2c7cb85f4144726561cefc86dcd"),
               unhexlify(b"ab3effd3a2706591774e013c76f5b8ece9e58abf7efc0a11b479f9d2a89d0c55"),
               unhexlify(b"ebf8d34e6643533bf73b13d2dd56aeaf2113fb3017d39bc6db6a2f71bc1d53f1"),
               ],
            R=[unhexlify(b"27e146e61e88944246dcd90ddb4284923c7fdc6fd6a187ed2efa3dcb8c380346"),
               unhexlify(b"fab99152d48d835b9a01cdbec46301db0f57ca091f6cbaa0b45c8498f18babe1"),
               unhexlify(b"8467f87acd7be026a27ed798cca6cc1526b0f805ac534a9c5162a9cd75460011"),
               unhexlify(b"f421fa4bda1dba042ca56c6bdce313dc8d18cee084d722af47447ce54b6ff8df"),
               unhexlify(b"8dd5dabc0ad67c83f42668e96bf5ee6741bcd8e661eda1e8ce6a23d84cf0b5b5"),
               unhexlify(b"fcf20a7775699b0456542930b2374b233fb3f8f79e1911428157631a20b3c3ad"),
               unhexlify(b"66e477bd93dabb184e2738829320bf8e60f6b4b476ca0fbc1013af28e8de34c1"),
               ],
        )

    def bproof_plus_2_invalid(self):
        return BulletproofPlus(
            V=[
                unhexlify(b"e0dae61095ac728a15d4d9754f1f9f956c22d4fa2deee2c0ff1def031b083e02"),
                unhexlify(b"5b424ecb1f8ea02351d324296a34a0608ecc104610feaad06e6002f61992bfe1"),
            ],
            A=unhexlify(b"6ae6f16a6b01cf494fb2cf368573365293f76c624cfc11152d648479238e9309"),
            A1=unhexlify(b"33ad318a44df6f14a945e6d051911ab9a24841457d15d62bd1436fb3edc8a193"),
            B=unhexlify(b"5f56531cb8e78dbb3450f1d599a6d4c7f5e4c04ee3e7015643c19a528bcbb109"),

            r1=unhexlify(b"40ad8a9c6b3bdd95c7fb8605e50135050e64f1ce29d1c4b37b1271e658354500"),
            s1=unhexlify(b"aed959c770499134aaa7e099f566dac56ee12959d797b62a3d8d1037b790b806"),
            d1=unhexlify(b"395a1e8d3df8e90e716fdeaa493090782c8db922337d09a36b50c1f02cd8e100"),

            L=[unhexlify(b"ed2d768bb9c8b5a9fa24c90b5831d3cceb3e78cef45eba90e52f89a2b3c859d2"),
               unhexlify(b"7f25cc8e211783e9c1b80dd13ee286943da0ec07bd33291536639432758f6927"),
               unhexlify(b"7bae3d31f4e2a6d78d74d2bcb6d0656e4222161423d635f7ce08805e96cec83e"),
               unhexlify(b"c87f949f70cf569c4baa332612305733fd19a2262490c55ec88c16a68d7b5e7d"),
               unhexlify(b"34d06caf0d02129ebcc8bf318da8f6a0ddfaf2c7cb85f4144726561cefc86dcd"),
               unhexlify(b"ab3effd3a2706591774e013c76f5b8ece9e58abf7efc0a11b479f9d2a89d0c55"),
               unhexlify(b"ebf8d34e6643533bf73b13d2dd56aeaf2113fb3017d39bc6db6a2f71bc1d53f1"),
               ],
            R=[unhexlify(b"27e146e61e88944246dcd90ddb4284923c7fdc6fd6a187ed2efa3dcb8c380346"),
               unhexlify(b"fab99152d48d835b9a01cdbec46301db0f57ca091f6cbaa0b45c8498f18babe1"),
               unhexlify(b"8467f87acd7be026a27ed798cca6cc1526b0f805ac534a9c5162a9cd75460011"),
               unhexlify(b"f421fa4bda1dba042ca56c6bdce313dc8d18cee084d722af47447ce54b6ff8df"),
               unhexlify(b"8dd5dabc0ad67c83f42668e96bf5ee6741bcd8e661eda1e8ce6a23d84cf0b5b5"),
               unhexlify(b"fcf20a7775699b0456542930b2374b233fb3f8f79e1911428157631a20b3c3ad"),
               unhexlify(b"66e477bd93dabb184e2738829320bf8e60f6b4b476ca0fbc1013af28e8de34c1"),
               ],
        )
    # fmt: on

    def test_verify_plus(self):
        bpi = bp.BulletProofPlusBuilder()
        bpi.verify_batch([self.bproof_plus_2()])
        bpi.verify_batch([self.bproof_plus_2(), self.bproof_plus_2()])
        with self.assertRaises(Exception):
            bpi.verify_batch([self.bproof_plus_2_invalid()])

    def test_prove_plus_1(self):
        bpi = bp.BulletProofPlusBuilder()
        sv = [crypto.Scalar(123)]
        gamma = [crypto.Scalar(456)]
        proof = bpi.prove_batch(sv, gamma)
        bpi.verify_batch([proof])

    def test_prove_plus_2(self):
        bpi = bp.BulletProofPlusBuilder()
        sv = [crypto.Scalar(123), crypto.Scalar(768)]
        gamma = [crypto.Scalar(456), crypto.Scalar(901)]
        proof = bpi.prove_batch(sv, gamma)
        bpi.verify_batch([proof])

    def test_prove_plus_16(self):
        bpi = bp.BulletProofPlusBuilder()
        sv = [crypto.Scalar(i * 123 + 45) for i in range(16)]
        gamma = [crypto.Scalar(i * 456 * 17) for i in range(16)]
        proof = bpi.prove_batch(sv, gamma)
        bpi.verify_batch([proof])


if __name__ == "__main__":
    unittest.main()
