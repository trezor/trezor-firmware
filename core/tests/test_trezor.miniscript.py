# flake8: noqa: F403,F405
from common import *  # isort:skip


from trezor import utils

if utils.USE_MINISCRIPT:
    from trezor import miniscript
    from trezor.crypto import hashlib

    from apps.bitcoin.addresses import encode_bech32_address

    TEST1_XPUB = "[00000000]xpub6DVwZpXox5Ufcug1ub1LXSuYzej9yTY26asDVveSYJA3d31JhFp25ofUC6cS37YvhWGH26oTbpUdipBYfCc47hWobdezL1cQLKDhCVFqez8"
    TEST2_XPUB = "[00000001]xpub6CFvZzxtB9b9dxhnMa7E6LhSwLXHsvKXtzpQgvYJh9miAftECi2mnnzEz5KLGEyz1MmetXTLhj93cQR4aeuW2oMnK5aczoLXuK57bbZBcN4"
    TEST3_XPUB = "[00000002]xpub6DFEv2BRUtXrNBMHzePBNEqDKSFDDBEgxnvne2ZgwReegyVFFGqthqJ8oyL9NzGtpWbSn5a2EdC4ffZELCFWW75794954to7uf7yeDFQypf"
    TEST4_XPUB = "[00000003]xpub6DJEDKjse8S92yvQx7JkXLk5aAhkJWXZa5XckxrPy28EwLB6jUzrCS77tAEpRWq3QqF2RivtzDt9ExsyxrqkG75xJty3fwVDvDdFBpmMwfu"
    TEST5_XPUB = "[00000004]xpub6DRQCUpZfs7b5vkVobwvSF2cH4BnnU8VjcLJw1WUGdSAbspFhqHRFRw8PDqgKFjL2xXSyyQc9nszDnRaPHsU4U36L6HsQPFxfUQM5o5rX7G"

    TEST1_TPUB = "tpubDCZB6sR48s4T5Cr8qHUYSZEFCQMMHRg8AoVKVmvcAP5bRw7ArDKeoNwKAJujV3xCPkBvXH5ejSgbgyN6kREmF7sMd41NdbuHa8n1DZNxSMg"
    TEST2_TPUB = "tpubDCNhwLKYSSu2FKssoMziAdwhAAKS3bASH7wZYkNmJ7sU5hW9LgDaAQPqe7ivAkskSF29B1CkRRg4g2mbovXgAL9Mby6i9xBdhZh2txDeSLb"

    POLICY_TEST1_XPUB = "xpub6DDUPHpUo4pcy43iJeZjbSVWGav1SMMmuWdMHiGtkK8rhKmfbomtkwW6GKs1GGAKehT6QRocrmda3WWxXawpjmwaUHfFRXuKrXSapdckEYF"
    POLICY_TEST2_XPUB = "xpub6DDUPHpUo4pd1hyVtRaknvZvCgdPdEDMKx3bB5UFcx73pEHRDVK4rwEZUgeUbVuYWGMNLvuBHp5WeyPevN2Gv7m9FnLHQE6XaKNRPZcYcHH"
    POLICY_TEST3_XPUB = "xpub6DDUPHpUo4pd5Z4Dmuk7igUc5DcYBoJXcVA1NJbKaRX1M2WKsTqHF5igMbwLpA23iHBwPXY11cidR2kiJVsQWfuJgaQJuxFrjm7iEhsMm4y"

    # From https://adys.dev/miniscript
    MORE_XPUBS = [
        "xpub6CX2v8gD4Lx1tQDrWfDk4RjDsWrqn1SX6Q2p8ACtWsjwSEtyA1HYGVpUNJExtjmsmpTh68h2BrVcRfFFBhJcSSz8SmXcF4crr3zNhKvRTRM",
        "xpub6By2dbMpSdtCVycBc2MjC949ksbuE6tHwVNk53zKEGfUrE2PGF3a3D2YLeokHJPDLHAnm7aGoxT47dWb6m3BmXmhbbKT7dqRXaAridfmRqq",
        "xpub6Ctf53JHVC5K4JHwatPdJyXjzADFQt7pazJdQ4rc7j1chsQW6KcJUHFDbBn6e5mvGDEnFhFBCkX383uvzq14Y9Ado5qn5Y7qBiXi5DtVBda",
        "xpub6BogqrbNGr4oC7TSMSxeAjWYGvCZ6ykK3m9XWUbH1B3wvs3JNNrXDKXjPSgfnHfyS1xJ6gis8Ngy5KCxkAD77zUjUMaM3CtrbDmUPFNoUAJ",
        "xpub6Bv82ixJNjgxru2C64FdNMT2zcpDtGCXwvbUwAajMjG2xspFuEws2a1FNCDbHfSYPJkE82bLdAKauQ3e4Ro5ToX2zGM9v8RRE9FUyVgtDw7",
    ]

    # BIP-39 mnemonic: 'cliff account add toe barrel hospital step naive coast betray crop chest'
    SAME_TPUB = "tpubDED8EAGWLhjBw5GSeBbP8AY87uvCHJdXmKDD2ARphtCQhLTCBvqa1Y29MvyoYho5daAJRMNEtDRBaqAM1Ehk7AAsspVqBcJGWD1Y3Anq9t3"

    # wsh(or_d(pk([5f5ac06b/48'/1'/0'/2']tpubDED8EAGWLhjBw5GSeBbP8AY87uvCHJdXmKDD2ARphtCQhLTCBvqa1Y29MvyoYho5daAJRMNEtDRBaqAM1Ehk7AAsspVqBcJGWD1Y3Anq9t3/<0;1>/*),and_v(v:pkh([5f5ac06b/48'/1'/0'/2']tpubDED8EAGWLhjBw5GSeBbP8AY87uvCHJdXmKDD2ARphtCQhLTCBvqa1Y29MvyoYho5daAJRMNEtDRBaqAM1Ehk7AAsspVqBcJGWD1Y3Anq9t3/<2;3>/*),older(1))))#p9svs5fv

    VECTORS = [
        (
            "wsh(pk({0}/<0;1>/*))",
            [TEST1_XPUB],
            [0, 1, "bc1q5ztlw2eq7xqdmqtzfpnu3jc2fv05r3eld3mjr4zpk0k9e4yrhwyq2ulchr"],
        ),
        (
            "wsh(or_d(pk({0}/<0;1>/*),and_v(v:pkh({1}/<0;1>/*),older(1))))",
            [TEST1_TPUB, TEST2_TPUB],
            [0, 1, "tb1qzvr7ptes6kq2ee0745a7h2n639etfz43nsz9d2jn8u6wz8egx0hqnr5pza"],
        ),
        (
            "wsh(or_d(pk({0}/<0;1>/*),and_v(v:pkh({0}/<2;3>/*),older(1))))",
            [SAME_TPUB],
            [0, 1, "tb1qkcqsdd5k4hg6vp0wc9nqksjq4qhpj0xjy6q04rf3c9ahzj9epjrsjwpj7c"],
            [0, 2, "tb1qlwmhydmvs25nq2vlz0ukt3hsz0lesz8unx79kvl2nhmcs9vzdyvq7uh86v"],
        ),
        (
            "wsh(or_i(and_v(v:thresh(2,pkh({0}/<2;3>/*),a:pkh({1}/<2;3>/*),a:pkh({2}/<0;1>/*)),older(52596)),and_v(v:pk({0}/<0;1>/*),pk({1}/<0;1>/*))))",
            [
                POLICY_TEST1_XPUB,
                POLICY_TEST2_XPUB,
                POLICY_TEST3_XPUB,
            ],
            [0, 1, "bc1qkye36enq7qzxadptuhh4v9t09zhelpw3cz9n0knvg2ayhdns5c7sc6vyde"],
        ),
        (
            "wsh(or_b(pk({0}/<0;1>/*),s:pk({1}/<0;1>/*)))",
            [TEST1_XPUB, TEST2_XPUB],
            [0, 2048, "bc1qyqwat6ts2wcwp0zj24vhz7vdky5rhef03np67d7nsuyh7j8w4z5sy6dcr0"],
            [1, 2048, "bc1q4j4dqp0ascxv9n6vmzkkw0fdj0agq2q5untuhf57mut99j5tqjqqy2mq2n"],
        ),
        (
            "wsh(and_v(v:pk({0}/<0;1>/*),andor(pk({1}/<0;1>/*),sha256(e258d248fda94c63753607f7c4494ee0fcbe92f1a76bfdac795c9d84101eb317),older(144))))",
            [TEST1_XPUB, TEST2_XPUB],
            [
                0,
                31415,
                "bc1qfd3tg4jld7ydyvcugvqkxmcjgga5j3kkyhwmh383468phu3vqvtsfzysfs",
            ],
            [
                1,
                31415,
                "bc1q0yrczjqxwdmh46dummxqcqz3vulk6h34shqs4wkkwdr3zkp0lzaq08c4yk",
            ],
        ),
        (
            "wsh(and_v(v:multi(2,{0}/<0;1>/*,{1}/<0;1>/*,{2}/<0;1>/*),after(1893456000)))",
            [TEST1_XPUB, TEST2_XPUB, TEST3_XPUB],
            [0, 77, "bc1q2p4v6zelvdq9zfzz56jq0zyjeae8cy6wadzrx0fe2zszw9s4e8tsml9p6q"],
            [1, 77, "bc1qt835665jr9422vut3234q95tf27jvggx7jry0cfl3kq9hr9ala4qsluma6"],
        ),
        (
            "wsh(or_d(pk({0}/<0;1>/*),and_v(v:thresh(3,pkh({1}/<0;1>/*),a:pkh({2}/<0;1>/*),a:pkh({3}/<0;1>/*),a:pkh({4}/<0;1>/*)),older(65535))))",
            [TEST1_XPUB, TEST2_XPUB, TEST3_XPUB, TEST4_XPUB, TEST5_XPUB],
            [0, 120, "bc1q73sxy54qdr0f2mgnqhd4felm67nm9tfg99w2grag3zz055ee3nxq0fdcxp"],
            [1, 120, "bc1ql0cpv6q85qlr6a2wcfg0lh3ms89f8z98sy9fc4m7q45k5r3kyf2s2z2v4g"],
        ),
        # Liana 5-of-5, decaying to 4-of-5 after 1 month, decaying to 5-of-5 after 1 year
        (
            "wsh(or_i(and_v(v:thresh(3,pkh({0}/<4;5>/*),a:pkh({1}/<4;5>/*),a:pkh({2}/<4;5>/*),a:pkh({3}/<4;5>/*),a:pkh({4}/<4;5>/*)),older(52596)),or_i(and_v(v:thresh(4,pkh({0}/<2;3>/*),a:pkh({1}/<2;3>/*),a:pkh({2}/<2;3>/*),a:pkh({3}/<2;3>/*),a:pkh({4}/<2;3>/*)),older(4383)),and_v(v:and_v(v:and_v(v:and_v(v:pk({0}/<0;1>/*),pk({1}/<0;1>/*)),pk({2}/<0;1>/*)),pk({3}/<0;1>/*)),pk({4}/<0;1>/*)))))",
            [TEST1_XPUB, TEST2_XPUB, TEST3_XPUB, TEST4_XPUB, TEST5_XPUB],
            [0, 1, "bc1qltk24j5pdvzw02rw2zxhgfw4r36xh7n4nxnxkp79vq2txwnexp0s7ma2fr"],
            [1, 1, "bc1qdd6l6edv708esuezzqe7dxcw7wgkfmz92utdz2c3pdlpmgcvtawqqxwdqx"],
            [0, 2, "bc1qv7gjkz0lga7dxttkt4rqr3kt6va29t0lhdln2ramzc9wkyjg6zmstskvru"],
            [1, 2, "bc1qldc8pxzl5rx7c3fgtwjqpwuad6xmujk4vznv8t7qhfhredcjptjs03mqyy"],
        ),
        # From https://adys.dev/miniscript
        (
            # Corporate Wallet
            "wsh(andor(pk({3}/0/0),after(1767225600),multi(2,{0}/0/0,{1}/0/0,{2}/0/0)))",
            MORE_XPUBS,
            [0, 0, "bc1q8ptytc24ztnhhe0ksd7ngq56sf5afe8erz6phhtw4yxh7yk5kx3q880634"],
        ),
        (
            # Emergency Recovery",
            "wsh(or_d(pk({0}/0/0),and_v(v:thresh(2,pkh({1}/0/0),a:pkh({2}/0/0),a:pkh({3}/0/0)),older(1008))))",
            MORE_XPUBS,
            [0, 0, "bc1qk6s8edzztsx0lfx5clr8xe6pxaz6wqmu0eah5u8jglg66zv7ldnsksr73p"],
        ),
        (
            # 2FA + Backup
            "wsh(and_v(v:pk({0}/0/0),andor(pk({1}/0/0),hash160(6c60f404f8167a38fc70eaf8aa17ac351023bef8),older(52560))))",
            MORE_XPUBS,
            [0, 0, "bc1qfr0lnd8ujtech9l5p6llh8wusz4779ezjt0xpz6ntnw3lzqspnhqkz98lv"],
        ),
        (
            # HODL Wallet
            "wsh(or_d(pk({0}/0/0),and_v(v:thresh(3,pkh({1}/0/0),a:pkh({2}/0/0),a:pkh({3}/0/0),a:pkh({4}/0/0)),older(52560))))",
            MORE_XPUBS,
            [0, 0, "bc1qy7sn46zry0x039ydl6j3jalj63vsuhg64c0s8ms9wuejz3mx9kpsqkga9y"],
        ),
        (
            # Timelocked Multisig
            "wsh(and_v(v:multi(2,{0}/0/0,{1}/0/0,{2}/0/0),after(1767225600)))",
            MORE_XPUBS,
            [0, 0, "bc1qtw2r0rs7u5cusde4lfvnepeshyuy87ujx5tudk30un6h6ujxj30sx9dyqs"],
        ),
        (
            # Atomic Swap
            "wsh(and_v(v:pk({0}/0/0),andor(pk({1}/0/0),sha256(e258d248fda94c63753607f7c4494ee0fcbe92f1a76bfdac795c9d84101eb317),older(144))))",
            MORE_XPUBS,
            [0, 0, "bc1qlxxylc6h34j5pw45yp4dnj9n9m2ney4cg97wawxe8jkpt7c4k0cqlxvlvl"],
        ),
        # Liana end-to-end tests
        (
            "wsh(or_d(pk({0}/<0;1>/*),and_v(v:pkh({1}/<0;1>/*),older(52596))))",
            [
                # ALL x 12
                "[5c9e228d/48'/1'/0'/2']tpubDEGquuorgFNbDrg8vepq1HnaV2mgQu9TcSBgBYfXw4AX8VMgkWqvkxHNuJmiah8iVnA3Hgj4cSvaGAXEnq814yC6hMEreckLsd7zyLL3o76",
                # GYM x 12
                "[72758bc3/84'/1'/0']tpubDCNhwLKYSSu2FKssoMziAdwhAAKS3bASH7wZYkNmJ7sU5hW9LgDaAQPqe7ivAkskSF29B1CkRRg4g2mbovXgAL9Mby6i9xBdhZh2txDeSLb",
            ],
            [0, 1, "tb1qx54dhwjrq3ay3zwvuazfa4k32lkhh20f9mqhtjvwc8n28z6ahrgq3pejk2"],
            [0, 2, "tb1qukdljlskapzsma2m37gpxhhad839nha4nx6tw88acvrtjp7d0zzq7cxmve"],
            [0, 3, "tb1q7ds7kun2m0cx8d9pv4ntln4n999mylzhedkqueluzxamednrfp4q5gt588"],
        ),
        (
            "wsh(or_d(pk({0}/<0;1>/*),and_v(v:pkh({1}/<0;1>/*),older(52596))))",
            [
                # ALL x 12
                "[5c9e228d/84'/1'/0']tpubDCZB6sR48s4T5Cr8qHUYSZEFCQMMHRg8AoVKVmvcAP5bRw7ArDKeoNwKAJujV3xCPkBvXH5ejSgbgyN6kREmF7sMd41NdbuHa8n1DZNxSMg",
                # GYM x 12
                "[72758bc3/48'/1'/0'/2']tpubDFEgneqafaLtGYbwidefdMyBZ3mxyoqyQZPPqjZ7AVKjwxSzDgRhgobENPu8Fn8gkJJtgKaFa6fbS9AuccZSeJqqXGy2x9BCgiJ6By3qRAJ",
            ],
            [0, 1, "tb1q8flw7jp2vzyy3cyc4pencyv7n5r5whtyg86khml7m63nhwmqyu7srck39z"],
            [0, 2, "tb1qc9lgsnd7jugn3yd9ayjf4dkarwppld5ue0khp6h6w4tyyhesnw5q23rr0x"],
            [0, 3, "tb1qtnmm2dltmkn6utxefexumunzylejs5meh6v6daq0j4c2gn74t0lqdqf84g"],
        ),
    ]


@unittest.skipUnless(utils.USE_MINISCRIPT, "requires miniscript")
class TestMiniscript(unittest.TestCase):
    def test_compile(self):
        for template, xpubs, *addrs in VECTORS:
            desc = template.format(*xpubs)
            for internal, index, expected in addrs:
                assert internal in (0, 1)
                script = miniscript.compile(desc, bool(internal), index)
                self.assertEqual(_wsh(hrp=expected[:2], script=script), expected)


def _wsh(hrp: str, script: bytes) -> str:
    return encode_bech32_address(hrp, witver=0, script=hashlib.sha256(script).digest())


if __name__ == "__main__":
    unittest.main()
