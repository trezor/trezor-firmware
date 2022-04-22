from common import *

if not utils.BITCOIN_ONLY:
    from apps.monero.xmr import bulletproof as bp, crypto, monero
    from apps.monero.xmr.serialize_messages.tx_rsig_bulletproof import Bulletproof, BulletproofPlus


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestMoneroBulletproof(unittest.TestCase):

    def test_square_multiply(self):
        for x in [2, 3, 16, 17, 31, 32]:
            ss = crypto.random_scalar()
            s1 = crypto.sc_copy(None, ss)
            s2 = crypto.sc_copy(None, ss)
            for i in range(1, x):
                crypto.sc_mul_into(s1, s1, ss)

            bp._sc_square_mult(s2, ss, x)
            self.assertEqual(crypto.encodeint_into(None, s1), crypto.encodeint_into(None, s2))

    def test_dvct_skips(self):
        z_sq = unhexlify(b'e0408b528e9d35ccb8386b87f39b85c724740644f4db412483a8852cdb3ceb00')
        d_vct0 = bp.VctD(64, 8, z_sq, raw=True)
        d_vct1 = bp.VctD(64, 8, z_sq, raw=True)
        tmp = crypto.Scalar()

        # Linear scan vs jump
        for i in range(65):
            tmp = d_vct0[i]
        self.assertEqual(crypto.encodeint_into(None, tmp), crypto.encodeint_into(None, d_vct1[64]))

        # Jumping around
        _ = d_vct0[128]
        self.assertEqual(crypto.encodeint_into(None, d_vct0[64]), crypto.encodeint_into(None, d_vct1[64]))

        # Sync on the same jump
        self.assertEqual(crypto.encodeint_into(None, d_vct0[65]), crypto.encodeint_into(None, d_vct1[65]))
        self.assertEqual(crypto.encodeint_into(None, d_vct0[65]), crypto.encodeint_into(None, d_vct1[65]))

        # Jump vs linear again, move_one vs move_more
        for i in range(1, 10):
            tmp = d_vct0[65 + i]
        self.assertEqual(crypto.encodeint_into(None, tmp), crypto.encodeint_into(None, d_vct1[74]))

        _ = d_vct0[85]
        _ = d_vct1[89]  # different jump sizes, internal state management test
        self.assertEqual(crypto.encodeint_into(None, d_vct0[95]), crypto.encodeint_into(None, d_vct1[95]))

        _ = d_vct0[319]  # move_one mults by z_sq then; enforce z component updates
        self.assertEqual(crypto.encodeint_into(None, d_vct0[320]), crypto.encodeint_into(None, d_vct1[320]))

        tmp = crypto.sc_copy(None, d_vct0[64])  # another jump back and forth
        _ = d_vct0[127]
        self.assertEqual(crypto.encodeint_into(None, d_vct0[64]), crypto.encodeint_into(None, tmp))

        _ = d_vct0[0]
        _ = d_vct1[0]
        _ = d_vct0[64]
        self.assertEqual(crypto.encodeint_into(None, d_vct0[5]), crypto.encodeint_into(None, d_vct1[5]))

    def test_pow_back_skips(self):
        MN = 128
        y = unhexlify('60421950bee0aab949e63336db1eb9532dba6b4599c5cd9fb1dbde909114100e')
        y_sc = crypto.decodeint_into(None, y)
        yinv = bp._invert(None, y)

        y_to_MN_1 = bp._sc_square_mult(None, y_sc, MN - 1)
        ymax = crypto.sc_mul_into(None, y_to_MN_1, y_sc)  ## y**MN
        ymax2 = bp._sc_square_mult(None, y_sc, MN)
        self.assertEqual(crypto.encodeint_into(None, ymax), crypto.encodeint_into(None, ymax2))

        size = MN + 1
        ypow_back = bp.KeyVPowersBackwards(size, y, x_inv=yinv, x_max=ymax, raw=True)
        self.assertEqual(crypto.encodeint_into(None, ymax), crypto.encodeint_into(None, ypow_back[MN]))

        for i in range(10):
            _ = ypow_back[MN - i]

        self.assertEqual(crypto.encodeint_into(None, ypow_back[MN - 9]),
                         crypto.encodeint_into(None, bp._sc_square_mult(None, y_sc, MN - 9)))
        self.assertEqual(crypto.encodeint_into(None, ypow_back[MN - 19]),
                         crypto.encodeint_into(None, bp._sc_square_mult(None, y_sc, MN - 19)))
        self.assertEqual(crypto.encodeint_into(None, ypow_back[MN - 65]),
                         crypto.encodeint_into(None, bp._sc_square_mult(None, y_sc, MN - 65)))
        self.assertEqual(crypto.encodeint_into(None, ypow_back[MN - 14]),
                         crypto.encodeint_into(None, bp._sc_square_mult(None, y_sc, MN - 14)))

        tmp = crypto.sc_copy(None, ypow_back[MN - 64])  # another jump back and forth
        _ = ypow_back[MN - 127]
        self.assertEqual(crypto.encodeint_into(None, ypow_back[MN - 64]), crypto.encodeint_into(None, tmp))
        self.assertEqual(crypto.encodeint_into(None, ypow_back[MN - 64]),
                         crypto.encodeint_into(None, bp._sc_square_mult(None, y_sc, MN - 64)))

    def test_bpp_bprime(self):
        N, M = 64, 4
        MN = N*M
        y = unhexlify(b'60421950bee0aab949e63336db1eb9532dba6b4599c5cd9fb1dbde909114100e')
        z = unhexlify(b'e0408b528e9d35ccb8386b87f39b85c724740644f4db412483a8852cdb3ceb00')
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

    def mask_consistency_check(self, bpi):
        sv = [crypto.Scalar(123)]
        gamma = [crypto.Scalar(432)]

        bpi.prove_setup(sv, gamma)
        x = bp._ensure_dst_key()
        y = bp._ensure_dst_key()

        sL = bpi.sL_vct(64)
        sR = bpi.sR_vct(64)

        self.assertEqual(sL.to(0, x), sL.to(0, y))
        self.assertEqual(sL.to(1, x), sL.to(1, y))
        self.assertEqual(sL.to(63, x), sL.to(63, y))
        self.assertNotEqual(sL.to(1, x), sL.to(0, y))
        self.assertNotEqual(sL.to(10, x), sL.to(0, y))

        self.assertEqual(sR.to(0, x), sR.to(0, y))
        self.assertEqual(sR.to(1, x), sR.to(1, y))
        self.assertEqual(sR.to(63, x), sR.to(63, y))
        self.assertNotEqual(sR.to(1, x), sR.to(0, y))

        self.assertNotEqual(sL.to(0, x), sR.to(0, y))
        self.assertNotEqual(sL.to(1, x), sR.to(1, y))
        self.assertNotEqual(sL.to(63, x), sR.to(63, y))

        ve1 = bp._ensure_dst_key()
        ve2 = bp._ensure_dst_key()
        bpi.vector_exponent(bpi.aL, bpi.aR, ve1)
        bpi.vector_exponent(bpi.aL, bpi.aR, ve2)

        bpi.vector_exponent(sL, sR, ve1)
        bpi.vector_exponent(sL, sR, ve2)
        self.assertEqual(ve1, ve2)

    # fmt: off
    def bproof_1(self):
        return Bulletproof(
            V=[
                unhexlify(b"3c705e1da4bbe43a0535a5ad3a8e6c148fb8c1a4118ba6b65412b2fe6511b261"),
            ],
            A=unhexlify(b"7372db75c0d9d409524924fff5dd13e867eb4c5789f3f5cc6ef860be68d5e4e5"),
            S=unhexlify(b"be8f2d87ace0a528056d567881e74f44817a811e110cdb3890376262a2084ab3"),
            T1=unhexlify(b"8dfc541c379efbe6000bb2339c3a52288ffa4300fcc0f0f0de777e54b5488160"),
            T2=unhexlify(b"cf7d046c86c33bea6c5167bb6482c0a31332989dc9493eacc04a07deb6536953"),
            taux=unhexlify(b"abaaf209cc9a800d933d51bb398b81ee7284efc9c92727066a640fdccc954009"),
            mu=unhexlify(b"ec743e23abb555dca26164a86614306f117a733fcd395eb8675411cd31915608"),
            L=[unhexlify(b"0ee1acc28126656eaf0934314a97e1cf2232a13f5636d319a233cedd58b2882f"),
               unhexlify(b"cc3d2ec5635de569343bea37fc46a93413ae66bf803a4333f427f79f341d1696"),
               unhexlify(b"518c80669bed0960fd03e802a9e837e1aa4a4910bb5853067447d7d22eaca325"),
               unhexlify(b"251a586e8e79a5d767b89931e012acdae317c13c434a6f5f121e44b3b59240b2"),
               unhexlify(b"09b41426e6c9808f6a58ded987cc39936f703f136b50493dd1c92c9b1ec4e7fc"),
               unhexlify(b"984d1369c3c7f2687eebca26395576810c66623408958efde4f36b0bb63a2475"),
               ],
            R=[unhexlify(b"31768a0465315ff0dd1ea2228ae8c34d1474e873a863362feab7b050f29a211a"),
               unhexlify(b"27d1b2533ed78d3dacc396afa50fa533cffc5d1563b679a4049a482436718d3c"),
               unhexlify(b"a49388b042c8a4c6526054661fac1706cf450181ec1f9eed005b283614ec7f95"),
               unhexlify(b"3f053243fe16f8fd302395c125ffedd93831829b13abbb195bf69fc139069de9"),
               unhexlify(b"5a32d7f7132043d1f0cc8cd88cce94e5241337ed616c35a1d753436b2d1c4a93"),
               unhexlify(b"bbd7f9b3031cf41b613a9ee726de9693457238b4be6317083d278e00717f8c14"),
               ],
            a=unhexlify(b"83d8d128f35aa02fc063792df9f4e9de0d4e58b8c6e7c449a672d6e4286ee309"),
            b=unhexlify(b"741d679f1dfe749f7d1ede687f8dd48f7fd3b5a52a5e6a453488d5e25b3fff0e"),
            t=unhexlify(b"88331e9fd7573135016629f337240225f9c0a5b70bad4157ad60d4260feb2b03")
        )

    def bproof_2(self):
        return Bulletproof(
            V=[
                unhexlify(b"3c705e1da4bbe43a0535a5ad3a8e6c148fb8c1a4118ba6b65412b2fe6511b261"),
                unhexlify(b"de5b617501a37ff257e05b0cf93041253fdb85126549640891f7471d4ede167c"),
            ],
            A=unhexlify(b"447843c57f05fc8d68c5fdc96fe09d3599aacfe9b25e403d67482fdbe8ffbdbb"),
            S=unhexlify(b"105b0186d1ec9a8e17e3f6f7909317458681275f888f6ac8a891ec3b5d51dfd5"),
            T1=unhexlify(b"552c8f7b1e382842feb79b982738350b0d7aeed850ac06bc86ca7c99e43fbfcc"),
            T2=unhexlify(b"2947b12ecc6c1667b0f0233ec1290893c992f655351edfd1ca877f8bcc070fc0"),
            taux=unhexlify(b"8cceaccd9626c55166e8892fa6a7e200f9db27e3b46619f6c84e20b3c7ab200c"),
            mu=unhexlify(b"c08a546e487b0c19e1e125c5dda6032bf198fe296d0dff52d58d091737a97b03"),
            L=[unhexlify(b"4c5f56522c1e239ccc7edd45b6cc03c7ea46c3d521953bf529989f9d5935a01d"),
               unhexlify(b"ba764db54e1ed9472df5d1527badd51be2a0223695a136d2114be631d135e1a9"),
               unhexlify(b"7fecaae48171615c9f282c146ade72befc0f88c402a178be133b5f51afd3dbfc"),
               unhexlify(b"3c66bbea3376133d8c571fced01b98ce96326fe233f311b4faf77564598d2021"),
               unhexlify(b"1179c7e24a6d7655bff0b5017ccb85b21f39822c6d845cb1894737a33030e17a"),
               unhexlify(b"461a200a1b5a7194c021faac7cda64a80388cea2ca26330ca06179aab409d6b1"),
               unhexlify(b"5e5c377a648ac4d5c900a1ea527a9358083aa1c7777085c3ef81d0316ed16b47"),
               ],
            R=[unhexlify(b"110ea38dd587c1f53a8211198cd033a982d173c4d1cdbb0873685a37c7126cb5"),
               unhexlify(b"960d6ef5dd857bb48148b4fb6927468d02f2a6474d535fd571b61c2c9b2b5613"),
               unhexlify(b"dd6454b5e029fe4ff8f9647be237a68d0de9457e742df9dafe6e20c1f6ead444"),
               unhexlify(b"ba9e3d1d9758184679283ee611144ed31d242700af13ac543bf5901472686d1a"),
               unhexlify(b"05db7c85b62d95dd74f56fab6e3eee3b72b01514640601200770869616b123d1"),
               unhexlify(b"b8b037b10f5647e79c7c5e7f735a554c8fb656037b304bd94383b769095bc17a"),
               unhexlify(b"43f4bd0bc55b60c73ab73bb5c3f9376165f815364dc97ae62de2447e0b428632"),
               ],
            a=unhexlify(b"0f7696d2b23cfd84f9b62ce906458580db6fe73aaba1682e0e17e4cb9dae1b02"),
            b=unhexlify(b"76541c70a127d08110a4bc09e6c6c6a0104956d089bcc0699f32dc5fde20ff03"),
            t=unhexlify(b"66b4498e8980dafea640ce36c763367aba1b415c2d469b564c96d718ff009d0a")
        )

    def bproof_2_invalid(self):
        return Bulletproof(
            V=[
                unhexlify(b"3c705e1da4bbe43a0535a5ad3a8e6c148fb8c1a4118ba6b65412b2fe6511b261"),
                unhexlify(b"de5b617501a37ff257e05b0cf93041253fdb85126549640891f7471d4ede167c"),
            ],
            A=unhexlify(b"447843c57f05fc8d68c5fdc96fe09d3599aacfe9b25e403d67482fdbe8ffbdbb"),
            S=unhexlify(b"005b0186d1ec9a8e17e3f6f7909317458681275f888f6ac8a891ec3b5d51dfd5"),
            T1=unhexlify(b"552c8f7b1e382842feb79b982738350b0d7aeed850ac06bc86ca7c99e43fbfcc"),
            T2=unhexlify(b"2947b12ecc6c1667b0f0233ec1290893c992f655351edfd1ca877f8bcc070fc0"),
            taux=unhexlify(b"8cceaccd9626c55166e8892fa6a7e200f9db27e3b46619f6c84e20b3c7ab200c"),
            mu=unhexlify(b"c08a546e487b0c19e1e125c5dda6032bf198fe296d0dff52d58d091737a97b03"),
            L=[unhexlify(b"4c5f56522c1e239ccc7edd45b6cc03c7ea46c3d521953bf529989f9d5935a01d"),
               unhexlify(b"ba764db54e1ed9472df5d1527badd51be2a0223695a136d2114be631d135e1a9"),
               unhexlify(b"7fecaae48171615c9f282c146ade72befc0f88c402a178be133b5f51afd3dbfc"),
               unhexlify(b"3c66bbea3376133d8c571fced01b98ce96326fe233f311b4faf77564598d2021"),
               unhexlify(b"1179c7e24a6d7655bff0b5017ccb85b21f39822c6d845cb1894737a33030e17a"),
               unhexlify(b"461a200a1b5a7194c021faac7cda64a80388cea2ca26330ca06179aab409d6b1"),
               unhexlify(b"5e5c377a648ac4d5c900a1ea527a9358083aa1c7777085c3ef81d0316ed16b47"),
               ],
            R=[unhexlify(b"110ea38dd587c1f53a8211198cd033a982d173c4d1cdbb0873685a37c7126cb5"),
               unhexlify(b"960d6ef5dd857bb48148b4fb6927468d02f2a6474d535fd571b61c2c9b2b5613"),
               unhexlify(b"dd6454b5e029fe4ff8f9647be237a68d0de9457e742df9dafe6e20c1f6ead444"),
               unhexlify(b"ba9e3d1d9758184679283ee611144ed31d242700af13ac543bf5901472686d1a"),
               unhexlify(b"05db7c85b62d95dd74f56fab6e3eee3b72b01514640601200770869616b123d1"),
               unhexlify(b"b8b037b10f5647e79c7c5e7f735a554c8fb656037b304bd94383b769095bc17a"),
               unhexlify(b"43f4bd0bc55b60c73ab73bb5c3f9376165f815364dc97ae62de2447e0b428632"),
               ],
            a=unhexlify(b"0f7696d2b23cfd84f9b62ce906458580db6fe73aaba1682e0e17e4cb9dae1b02"),
            b=unhexlify(b"76541c70a127d08110a4bc09e6c6c6a0104956d089bcc0699f32dc5fde20ff03"),
            t=unhexlify(b"66b4498e8980dafea640ce36c763367aba1b415c2d469b564c96d718ff009d0a")
        )

    def bproof_4(self):
        return Bulletproof(
            V=[
                unhexlify(b"8bb0da134d14ad399af3b3ab476afbf3a9ad39c610d770ad86be8f8fcf4d5334"),
                unhexlify(b"5321769a89359b519df85e8aaf9d310920641a09796b1c07917c505dfea3c638"),
                unhexlify(b"4b7dfc193c8e717f66f8811aa30ed5aa27cde9f5b64826346c96040be6311256"),
                unhexlify(b"e3a5474501cef576428521ab71c17676477ea75ca2de0f1950cc62a91831bb4b"),
            ],
            A=unhexlify(b"d5be7a928f686ac09eaa8d18c3329e587d6e8e8cc9a35f50a747a128c94da69a"),
            S=unhexlify(b"35654816c07d7537e1091bbe5768eb5733c986b642aad9e1ecf8e2d9dca5894e"),
            T1=unhexlify(b"b0fcf5c8e6b23bbcbbc7e31776ba08166b01a3fb22930f871c5afae01c5bfa30"),
            T2=unhexlify(b"a918af0bfb87b142ef86ef4cebff56e7ff372ac554f5bb50e11ef9cf730eb984"),
            taux=unhexlify(b"f8596b4f35387c2b7bbda10bc668f4233c1c34ec9ab702e5064476182de38405"),
            mu=unhexlify(b"5ebde106b2c6096808e359dddaec2d9e0dc558a38f9958fabb60dd90ba3a1701"),
            L=[unhexlify(b"a98b5961c6988f9a31a9fd982e5e992f0c899edf91ba09d87f254eff45e20c88"),
               unhexlify(b"81e161c3b3573fcf8f5e365a01b2882b1dbacc1dbf273eba984eb8ae575794e6"),
               unhexlify(b"0b3c65d81b2d0384aa2d3ec128e880b2385f6c7de942a5f906d84d930f458798"),
               unhexlify(b"38fc712591ca80d106e0d207a9342d7fea1be529909de7aeb3df1e6e805520f5"),
               unhexlify(b"8cc71b0aa59c67f1f9c3f0f6f64e8feb3622406a45f9575cd96697fdfce98ba8"),
               unhexlify(b"8456936b65204ec32bc5e378485d6d7931581cf9f5d734c5af34a3dde67de785"),
               unhexlify(b"4fca68547aea92ab546e33d43151821b94c153cc045388a4b409276c8c52110b"),
               unhexlify(b"197f85a00316bee804a89f215b91edb5e259e92b002bf7a410174fc8b5987e6c"),
               ],
            R=[unhexlify(b"02a06fa825460b77fb3bdc6724da7849b81ecd98602cd666720235319133673a"),
               unhexlify(b"bc633534483f4e6a86133281d6d841c81d75e3305785463d55b1991c2e2d5492"),
               unhexlify(b"c816c4d05b92288d0d6431513bfbcbdefd15e39cfc665ea6445ebb8903811931"),
               unhexlify(b"27def4cc98f1c7c43aed78968aacc3fb06394ebf305de4495998cd3e6cbb515a"),
               unhexlify(b"9a54fba6a21aafc95c3e80639558b6608257e3289dc005855b37245f6f5a0d85"),
               unhexlify(b"495dd5d57df30aff8be48f538142c2c50d04675953286dbd82095cb7e9ec45f7"),
               unhexlify(b"d504b4927875bf39651c4593a4dc27d78a14ff0ddc46b056c0bcd1d6ab5dce90"),
               unhexlify(b"80a87eb25f02539fbb44649c477ce0044e7ec8e99410d16242796aad168f6731"),
               ],
            a=unhexlify(b"ae3789e27324e3d4ecc48993b83052a8843fdcc67e1e4d30221e2dba4dd3c205"),
            b=unhexlify(b"4206e54ee16aaba98c43ab34ce7b094c05bc1d5c89c2cfc15436346f808fc305"),
            t=unhexlify(b"91ac52bd644dd0cf47064c340a0fb7e87f66eee3f9286af0f75a910260f46406")
        )

    def bproof_8(self):
        return Bulletproof(
            V=[
                unhexlify(b"8968230f6104ecadab81a61b71d7e5d35b62fb5e983ef0fa143f399e1b455556"),
                unhexlify(b"3ad4c8fc2476f239767b2c98b8adbd613e1d48290577ac2f060e5eae4578bc07"),
                unhexlify(b"5bfa33de351ec800057b9a94009cbe3c4b2207f8518adf338db39a4a541f99fb"),
                unhexlify(b"65ad56ed1e1253f3f6d912e46ce76a59f1e0ce76133e94c6fcff06aa8e57847f"),
                unhexlify(b"0b6c65c33a06a5fe402c735c5e58981e9cc5ed6d7020df746d828b203566010f"),
                unhexlify(b"eb01d17406d4b71b5b01358c3a8187da02de64cd6a18dcaaff107e1c0310283b"),
                unhexlify(b"5826183d16cc353b8b07778354b4d5e4bec71c9c915b8db4cd314e1a4fc8515c"),
                unhexlify(b"cf980756a69c3535f9a52897e13cb3649211bc9870246b8456a55311b9d47b65"),
            ],
            A=unhexlify(b"9a8aa683d90464a9a02ab9d002bdaf04d306c271285caa916d0275bfed5786a8"),
            S=unhexlify(b"6eee7bf4b3b9fd00b0018c4a95d9e0dbdf4a4d8d68891c212a99ae040fad12db"),
            T1=unhexlify(b"d8b154556661544b0967529ddbb1650d8e82f6c43a2698f4191e36f815c44106"),
            T2=unhexlify(b"21a987b97cebcc51116dcdffc0576a8d727970bc5e075d4c885c9612ec53f01a"),
            taux=unhexlify(b"3f7b2ea15183fed911215d05d839907d057f324c01e630bb66dfb7f2e939f601"),
            mu=unhexlify(b"86440d5b853a4d39b43a05346535f6c62d434d3543eda161c2415f8a62387403"),
            L=[unhexlify(b"110ddcd1c72e576fa2a7388a31e5632779a15394a8f82c6db4a16aa12ee8c673"),
               unhexlify(b"0013e290ca6453f4327d79a010d7158588e4df5da07e64913ec460ebf1992729"),
               unhexlify(b"1f4af7b9e76c84fdd28ed1419f9b7d90f42c87399f8aca81b52dcf4f22dcf4db"),
               unhexlify(b"2e05fcc9835dac5e6a3124068726fdcfab49e6c5215dcb0d6ccf55befacbcc10"),
               unhexlify(b"0a8564bb2c7938382541e2f51996eb0d8c9a944a1c4c7abba51938fd3a2498b1"),
               unhexlify(b"a3b02cdbe3af1bb9f5961cdee787b1a55ce1e083cd4377543e7c11b3aa3a4789"),
               unhexlify(b"1d3301fe9b7438dcced3ca052a364aa442b1abe189f4013003e7ec8245331e5a"),
               unhexlify(b"31a0387da1091c18618ffc85ae1c84774ddd3885e6f9a525e108dab92333151a"),
               unhexlify(b"550e00179778a332d960438d443caab60b571c878787c3dc90a056cb102c47bb"),
               ],
            R=[unhexlify(b"b8d336c3521a854856bd1f78d8c7566f4cfe1441af74f38562bca947d98ab884"),
               unhexlify(b"b5514c68e2765ee4c39af1c65360a42f76e2538cea04de97e4e5cfb159fa46bc"),
               unhexlify(b"9f41d7fa770cae09b83600a5852ed36ef3418ec9bca566881046db6ceddaa87a"),
               unhexlify(b"b9dfcd2f889ccff138b98e84aad4cbbcb1723db0722950b421f0c7f7ca550312"),
               unhexlify(b"6fdcc16d2f6c202a2c386eb7d3b61dad86b8fe7d2c4d87c73a87fd87fa931828"),
               unhexlify(b"90aa28db8b75a86c7a867ae8323b5e327086047fe88131230c874fcae818a711"),
               unhexlify(b"398bfe592022ec1c801e13bd35577d563faa727d37f37daea5977c8abe584d69"),
               unhexlify(b"7dd85aff7c63f98b65384e0439407db98df9428f0375b7d7581291e519b097ec"),
               unhexlify(b"27a37d34a9f0fc5e1b7f20256a2b59b19954b52ae39f29870731750dab52bb1f"),
               ],
            a=unhexlify(b"de7d5bebe81a3ca0cb151e187e078ce98e7c19cc3f4ba448c2ccadee969a0f0a"),
            b=unhexlify(b"f8f88ee64bc03c68fa40d855f96b3d9f0cf16e3035aef3a129f76c89196b7207"),
            t=unhexlify(b"e9f0f74b2efcff21ac16c842e27b79d6615a31873be399d38e257a85bcc7c00b")
        )

    def bproof_16(self):
        return Bulletproof(
            V=[
                unhexlify(b"fcb9064e19894c5703f49d515ab0e6e98c87f9ec4230f0b898bc22061bb8d39f"),
                unhexlify(b"507ff564c127cc2beb83c9a539408ffd2ec5f648dda711724bba1a8b79d66e32"),
                unhexlify(b"dbd4de0ef0184378c483b9e821a6da2d80ed24d0c7444104efa4bbc710ed14ef"),
                unhexlify(b"8baeb7c9d69946547a8f73cdb0e6fae3134fe5e1734e8bbefe8bb452da1ae59e"),
                unhexlify(b"7f28196a49a4130b68b5589df47d9a2a08dc27518809016a3753ab2db4d8c453"),
                unhexlify(b"708ad84f91f702dbcdeee179f7e94328314190935ada0f85eddd5db35d631c8c"),
                unhexlify(b"3925935ecd1d2bb5fda9a15a822db8128c045b1b9fa017f4913231289329ff41"),
                unhexlify(b"d75438e7d308bb758e68d6af7d80087755dcffc0a47255ce17c2f653501997ef"),
                unhexlify(b"dd24a43fc1c31240c7d64248bd100e4ed7cefd9bd80ac05471ce947a71176de6"),
                unhexlify(b"c0011f8ae31c76f3658eb971bb520cac0d051fee4e5cf3ba833d55e093643f08"),
                unhexlify(b"c7b7edc4c584a1cc41b079550ce9e6ff7bc781b52d16c0c4b667988f422d66a8"),
                unhexlify(b"483d8df224106bbb6f45f50becbc70b55bbcbd262c0447a42d16f62ad57c057d"),
                unhexlify(b"9af16713061f6a43112092a3221a07ab7dd377145dc705611ad03f7cc407626a"),
                unhexlify(b"74b066e1866043d736bde08a790879e5387838e793fbdfb1e05d11404ad4c08f"),
                unhexlify(b"add0f5a30bf8111541ce5ab176bebf77f0b470f5ccac57ec5fda1dd5da641dfd"),
                unhexlify(b"d74989bc336a0557a027ad440683406273ca4d04d4138eac69107074ea7e18ed"),
            ],
            A=unhexlify(b"a66ce244c86883c8b8ef5ad8e38b3cb8db00306698813f9858edb226d294e52d"),
            S=unhexlify(b"34be5df1324bd561fd94695eb4b6e084068f188039831ca81be0e77849b639a7"),
            T1=unhexlify(b"6a86c12f2c1bd2c2c43193da1a1b4c13e8829c0583318977417a6e1144e3c1e9"),
            T2=unhexlify(b"f16761fd77f03a3d74854fe33143e2b02274747f27c6a4b45973622a0d1cec73"),
            taux=unhexlify(b"272decc39da7103cddfa0dc7ea4042ea313ab3f740c9234d060d35db04b9700b"),
            mu=unhexlify(b"acaa00e33078217cc1ee795e2886b771dded4da964ea8db682b7c4a9039c4906"),
            L=[unhexlify(b"f964f4a86362e788978371d38052e825e22e17e8e52a82a5b61cff4447516d1d"),
               unhexlify(b"ea7d1b2e10fb0aa15b8bf4be7300c0619036a0846bc0ae4ef62eca61fd2545f3"),
               unhexlify(b"d4cdfb68a899503f317edd6050da54e85a2979c7b145c10c76f69899a1dee450"),
               unhexlify(b"9c56aadad7366addf6c7ea3e39bde810056dd59ee9a6020109c92e8939734583"),
               unhexlify(b"56685894507fdbb994ff007f94ac16ad5b5d7e4cec2a2de6bbc0c0532b5cb190"),
               unhexlify(b"023f99b43ae8509446f625241bf263052c141a49f02356ff65d9eeec287ecd05"),
               unhexlify(b"eee0982bd28d2e85f0712d043879c00c1899de69ab1362cc0ac5369b3b17f32d"),
               unhexlify(b"8d4f9f498d376fda7b06a5dd95be852b32b65d6e2e38363f3e805477e996eec4"),
               unhexlify(b"e5d9ee5f8910b67c1cc02232e8bb018f0c39966f76b34aee2ce3441fd2737da2"),
               unhexlify(b"620ab92c82b294a97815d06548a4ac669228d04551c24d174902db1cbb8f10aa"),
               ],
            R=[unhexlify(b"a7b55c962351bd40dffe898a5192a3f05a6a89a0e3e61d6a2c4af27640c9cafe"),
               unhexlify(b"010a1259e188677332b3e3b60030f9b8fe57ff95d4ff4a3c110a147f26a0bf07"),
               unhexlify(b"891a65627a950b55428d86e2face1543b3297ec5d13839d7de684d92a9c7626b"),
               unhexlify(b"382e4354aad61f42223c9ff903aee83557716130bb159645ac48e8d27485feb9"),
               unhexlify(b"e8cd6098fdf7fba0f03db32e0fd41b549bfeaf489bfccf72c391fba9d5046737"),
               unhexlify(b"ed15099d4d39a73dc48a338246828c6ce60c8f68b648a0d205bf65b3d5a3623b"),
               unhexlify(b"8d1deb97bbfb33bec7dda8f56428a588a92512ee41ebdcb7b2f7631fc45d1a12"),
               unhexlify(b"35bd424cef108222b900b58078b90387a65c70f3fd1e1367dd827ee172f393fd"),
               unhexlify(b"63ecb848be5fab31d355c976876abd892cdc9d0ebc90e90cd8dab46e7f417740"),
               unhexlify(b"9189a79c56400ac08d8821d283d94f1f5ebebaf6f9660a62c995fccb192431d6"),
               ],
            a=unhexlify(b"e43b7890911f413e0d870f099961da40d8e053d9ddd21a56f7eb3308828dbc04"),
            b=unhexlify(b"dfea0fe39d9a7c5497fd01e92fc7fa8b39cda75b340322f77e0cac15194aa007"),
            t=unhexlify(b"0de43b393686af8dd0d89f4832a2995cda14e6288de9ecd2b4bf2fa39baba408")
        )

    def bproof_plus_1(self):
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
        # fmt: on

    def test_masks(self):
        bpi = bp.BulletProofBuilder()
        self.mask_consistency_check(bpi)

        # Randomized masks
        bpi.use_det_masks = False
        self.mask_consistency_check(bpi)

    def test_verify(self):
        bpi = bp.BulletProofBuilder()
        self.assertTrue(bpi.verify(self.bproof_1()))
        self.assertTrue(bpi.verify(self.bproof_2()))
        self.assertTrue(bpi.verify(self.bproof_4()))

    def test_prove(self):
        bpi = bp.BulletProofBuilder()
        val = crypto.Scalar(123)
        mask = crypto.Scalar(432)

        bp_res = bpi.prove(val, mask)
        bpi.verify(bp_res)

    def test_prove_2(self):
        bpi = bp.BulletProofBuilder()
        val = crypto.Scalar((1 << 30) - 1 + 16)
        mask = crypto.random_scalar()

        bp_res = bpi.prove(val, mask)
        bpi.verify(bp_res)

    def test_verify_batch_1(self):
        bpi = bp.BulletProofBuilder()
        bpi.verify_batch([self.bproof_1()])
        bpi.verify_batch([self.bproof_2()])
        bpi.verify_batch([self.bproof_4()])
        bpi.verify_batch([self.bproof_8()])
        bpi.verify_batch([self.bproof_16()])
        with self.assertRaises(Exception):
            bpi.verify_batch([self.bproof_2_invalid()])
        with self.assertRaises(Exception):
            bpi.verify_batch([self.bproof_2_invalid()])

    def test_verify_plus(self):
        bpi = bp.BulletProofPlusBuilder()
        bpi.verify_batch([self.bproof_plus_1()])

    def test_prove_plus_(self):
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

    def test_prove_plus_8(self):
        bpi = bp.BulletProofPlusBuilder()
        sv = [crypto.Scalar(i*123 + 45) for i in range(8)]
        gamma = [crypto.Scalar(i*456 * 17) for i in range(8)]
        proof = bpi.prove_batch(sv, gamma)
        bpi.verify_batch([proof])

    def test_prove_random_masks(self):
        bpi = bp.BulletProofBuilder()
        bpi.use_det_masks = False  # trully randomly generated mask vectors
        val = crypto.Scalar((1 << 30) - 1 + 16)
        mask = crypto.random_scalar()

        bp_res = bpi.prove(val, mask)
        bpi.verify(bp_res)

    def ctest_multiexp(self):
        scalars = [0, 1, 2, 3, 4, 99]
        point_base = [0, 2, 4, 7, 12, 18]
        scalar_sc = [crypto.Scalar(x) for x in scalars]
        points = [crypto.scalarmult_base_into(None, crypto.Scalar(x)) for x in point_base]

        muex = bp.MultiExp(scalars=[crypto.encodeint(x) for x in scalar_sc],
                           point_fnc=lambda i, d: crypto.encodepoint(points[i]))

        self.assertEqual(len(muex), len(scalars))
        res = bp.multiexp(None, muex)
        res2 = bp.vector_exponent_custom(
            A=bp.KeyVEval(3, lambda i, d: crypto.encodepoint_into(crypto.scalarmult_base_into(None, crypto.Scalar(point_base[i])), d)),
            B=bp.KeyVEval(3, lambda i, d: crypto.encodepoint_into(crypto.scalarmult_base_into(None, crypto.Scalar(point_base[3+i])), d)),
            a=bp.KeyVEval(3, lambda i, d: crypto.encodeint_into(crypto.Scalar(scalars[i]), d),),
            b=bp.KeyVEval(3, lambda i, d: crypto.encodeint_into(crypto.Scalar(scalars[i+3]), d)),
        )
        self.assertEqual(res, res2)

    def test_prove_batch(self):
        bpi = bp.BulletProofBuilder()
        sv = [crypto.Scalar(123), crypto.Scalar(768)]
        gamma = [crypto.Scalar(456), crypto.Scalar(901)]
        proof = bpi.prove_batch(sv, gamma)
        bpi.verify_batch([proof])

    def test_prove_batch16(self):
        bpi = bp.BulletProofBuilder()
        sv = [crypto.Scalar(137*i) for i in range(16)]
        gamma = [crypto.Scalar(991*i) for i in range(16)]
        proof = bpi.prove_batch(sv, gamma)
        bpi.verify_batch([proof])


if __name__ == "__main__":
    unittest.main()
